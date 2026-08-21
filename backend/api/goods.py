from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from db.db import async_session_maker
from db.ozon.dao import OzonItemDAO, OzonItemHistoryDAO, OzonItemFeedbackDAO, OzonItemCategoryDAO
from backend.schemas.goods import GoodsCreate, GoodsUpdate, GoodsOut, StockHistoryRequest, StockHistoryEntry
from backend.core.dependencies import get_current_user
from db.user.models import User
from backend.services.parser import get_data_by_url
from logging import Logger

logger = Logger(__name__)

router = APIRouter()

async def enrich_goods_item(item, session):
    """Вспомогательная функция для подгрузки категории и последней цены"""
    # Получаем категорию (первую)
    categories = await OzonItemCategoryDAO.find_all(item_id=item.id)
    category = categories[0].category if categories else None

    # Получаем последнюю цену из истории
    history = await OzonItemHistoryDAO.find_all(item_id=item.id)
    price = None
    if history:
        # Сортируем по дате убывания и берём первую
        sorted_history = sorted(history, key=lambda h: h.record_date, reverse=True)
        price = sorted_history[0].price

    # Формируем словарь для ответа
    return {
        "id": item.id,
        "name": item.cardname or "",
        "description": item.description or "",
        "url": item.url,
        "created_at": item.created_at,
        "updated_at": None,
        "product_id": item.product_id,
        "provider": item.provider,
        "brand": item.brand,
        "original_price": item.original_price,
        "currency": item.currency,
        "rating": item.rating,
        "reviews_count": item.reviews_count,
        "main_imgs": item.main_imgs or [],
        "desc_imgs": item.desc_imgs or [],
        "category": category,
        "price": price,
    }

@router.get("", response_model=List[GoodsOut])
async def get_goods(current_user: User = Depends(get_current_user)):
    async with async_session_maker() as session:
        items = await OzonItemDAO.find_all(user_id=current_user.id)
        if items is None:
            return []
        result = []
        for item in items:
            enriched = await enrich_goods_item(item, session)
            result.append(enriched)
        return result

@router.get("/{goods_id}", response_model=GoodsOut)
async def get_goods_by_id(goods_id: int, current_user: User = Depends(get_current_user)):
    async with async_session_maker() as session:
        item = await OzonItemDAO.find_one_or_none(id=goods_id, user_id=current_user.id)
        if not item:
            raise HTTPException(status_code=404, detail="Товар не найден")
        return await enrich_goods_item(item, session)

@router.post("", response_model=GoodsOut, status_code=status.HTTP_201_CREATED)
async def create_goods(goods: GoodsCreate, current_user: User = Depends(get_current_user)):
    async with async_session_maker() as session:
        goods_url = goods.url
        parsed_data = await get_data_by_url(goods_url)
        if not parsed_data.get("success"):
            raise HTTPException(status_code=400, detail="Не удалось распарсить товар по указанному URL")

        product_data = parsed_data["product_data"]

        # Создаём основной товар со всеми полями
        new_item = await OzonItemDAO.add(
            user_id=current_user.id,
            cardname=product_data.get("title", ""),
            description=product_data.get("description", ""),
            url=goods_url,
            product_id=product_data.get("product_id"),
            provider=product_data.get("provider"),
            brand=product_data.get("brand"),
            original_price=product_data.get("original_price"),
            currency=product_data.get("currency"),
            rating=product_data.get("rating"),
            reviews_count=product_data.get("reviews_count"),
            main_imgs=product_data.get("main_imgs", []),
            desc_imgs=product_data.get("desc_imgs", [])
        )
        if new_item is None:
            raise HTTPException(status_code=500, detail="Ошибка создания товара")

        # Сохраняем категорию
        category_name = product_data.get("category")
        if category_name:
            await OzonItemCategoryDAO.add(
                item_id=new_item.id,
                category=category_name
            )

        # Сохраняем историю (цена, рейтинг, отзывы)
        price = product_data.get("price")
        rating = product_data.get("rating")
        reviews_count = product_data.get("reviews_count")
        if price is not None or rating is not None or reviews_count is not None:
            await OzonItemHistoryDAO.add(
                item_id=new_item.id,
                record_date=datetime.now().date(),
                price=price,
                rating=rating,
                reviews_count=reviews_count,
                fbs_count=0
            )

        # Сохраняем отзывы
        reviews = product_data.get("reviews", {})
        for review_uuid, review_data in reviews.items():
            review_date_str = review_data.get("review_date")
            if review_date_str:
                try:
                    feedback_date = datetime.strptime(review_date_str, '%d.%m.%Y').date()
                except ValueError:
                    feedback_date = None
            else:
                feedback_date = None

            await OzonItemFeedbackDAO.add(
                item_id=new_item.id,
                feedback=review_data.get("review_text", ""),
                feedback_date=feedback_date
            )

        # Возвращаем обогащённый объект
        return await enrich_goods_item(new_item, session)
    
@router.delete("/{goods_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goods(goods_id: int, current_user: User = Depends(get_current_user)):
    async with async_session_maker() as session:
        # Проверяем, что товар существует и принадлежит пользователю
        item = await OzonItemDAO.find_one_or_none(id=goods_id, user_id=current_user.id)
        if not item:
            raise HTTPException(status_code=404, detail="Товар не найден")
        # Удаляем товар
        try:
            await OzonItemDAO.delete(id=goods_id)
        except Exception as e:
            logger.error(f"Delete error: {e}")
            raise HTTPException(500, f"Ошибка удаления: {str(e)}")
        return None  # 204 No Content


@router.post("/{goods_id}/stock-history", status_code=200)
async def update_stock_history(
    goods_id: int,
    payload: StockHistoryRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Обновить или добавить записи об остатках товара на складе (fbs_count).
    Принимает массив записей с датой и количеством.
    """
    async with async_session_maker() as session:
        # Проверяем, что товар принадлежит пользователю
        item = await OzonItemDAO.find_one_or_none(id=goods_id, user_id=current_user.id)
        if not item:
            raise HTTPException(status_code=404, detail="Товар не найден или доступ запрещён")

        # Обрабатываем каждую запись
        for entry in payload.entries:
            await OzonItemHistoryDAO.upsert_stock(
                item_id=goods_id,
                record_date=entry.record_date,
                fbs_count=entry.fbs_count
            )

        return {"message": f"Обновлено {len(payload.entries)} записей истории остатков."}