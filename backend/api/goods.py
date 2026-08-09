from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from db.db import async_session_maker
from db.ozon.dao import OzonItemDAO, OzonItemHistoryDAO, OzonItemFeedbackDAO, OzonItemCategoryDAO
from backend.schemas.goods import GoodsCreate, GoodsUpdate, GoodsOut
from backend.core.dependencies import get_current_user
from db.user.models import User
from backend.services.parser import get_data_by_url

router = APIRouter()

@router.get("", response_model=List[GoodsOut])
async def get_goods(current_user: User = Depends(get_current_user)):
    async with async_session_maker() as session:
        items = await OzonItemDAO.find_all(user_id=current_user.id)
        if items is None:
            return []
        result = []
        for item in items:
            result.append({
                "id": item.id,
                "name": item.cardname or "",
                "description": item.description or "",
                "url": item.url,
                "created_at": item.created_at.isoformat() if item.created_at else "",
                "updated_at": None,  # у нас нет поля updated_at в модели OzonItem
            })
        return result

@router.post("", response_model=GoodsOut, status_code=status.HTTP_201_CREATED)
async def create_goods(goods: GoodsCreate, current_user: User = Depends(get_current_user)):
    async with async_session_maker() as session:
        goods_url = goods.url

        # 1. Парсим данные по URL
        parsed_data = await get_data_by_url(goods_url)
        if not parsed_data.get("success"):
            raise HTTPException(status_code=400, detail="Не удалось распарсить товар по указанному URL")

        product_data = parsed_data["product_data"]

        # 2. Создаём основной товар
        new_item = await OzonItemDAO.add(
            user_id=current_user.id,
            cardname=product_data.get("title", ""),
            description=product_data.get("description", ""),
            url=goods_url,
        )
        if new_item is None:
            raise HTTPException(status_code=500, detail="Ошибка создания товара")

        # 3. Сохраняем категорию (если есть)
        category_name = product_data.get("category")
        if category_name:
            await OzonItemCategoryDAO.add(
                item_id=new_item.id,
                category=category_name
            )

        # 4. Сохраняем историю (цена, рейтинг, кол-во отзывов)
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
                fbs_count=0  # пока нет данных
            )

        # 5. Сохраняем отзывы
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

        # 6. Возвращаем созданный товар
        return {
            "id": new_item.id,
            "name": new_item.cardname or "",
            "description": new_item.description or "",
            "url": new_item.url,
            "created_at": new_item.created_at.isoformat() if new_item.created_at else "",
            "updated_at": None,
        }

@router.get("/{goods_id}", response_model=GoodsOut)
async def get_goods_by_id(goods_id: int, current_user: User = Depends(get_current_user)):
    async with async_session_maker() as session:
        item = await OzonItemDAO.find_one_or_none(id=goods_id, user_id=current_user.id)
        if not item:
            raise HTTPException(status_code=404, detail="Товар не найден")
        return {
            "id": item.id,
            "name": item.cardname or "",
            "description": item.description or "",
            "url": item.url,
            "created_at": item.created_at.isoformat() if item.created_at else "",
            "updated_at": None,
        }
    
@router.delete("/{goods_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goods(goods_id: int, current_user: User = Depends(get_current_user)):
    async with async_session_maker() as session:
        # Проверяем, что товар существует и принадлежит пользователю
        item = await OzonItemDAO.find_one_or_none(id=goods_id, user_id=current_user.id)
        if not item:
            raise HTTPException(status_code=404, detail="Товар не найден")
        # Удаляем товар
        await OzonItemDAO.delete(id=goods_id)
        return None  # 204 No Content