from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from db.db import async_session_maker
from db.ozon.dao import OzonDAO
from backend.schemas.goods import GoodsCreate, GoodsUpdate, GoodsOut
from backend.core.dependencies import get_current_user
from db.user.models import User

router = APIRouter()

# Убираем слеш в декораторах — теперь запросы на /goods (без слеша) будут обрабатываться
@router.get("", response_model=List[GoodsOut])
async def get_goods(current_user: User = Depends(get_current_user)):
    async with async_session_maker() as session:
        items = await OzonDAO.find_all(user_id=current_user.id)
        # Преобразуем модель OzonItem в схему GoodsOut
        result = []
        for item in items:
            # В вашей модели cardnames, urls_of_cards и т.д. – массивы, 
            # поэтому берём первый элемент для простоты
            result.append({
                "id": item.id,
                "name": item.cardnames[0] if item.cardnames else "",
                "description": item.descriptions[0] if item.descriptions else "",
                "article": "",  # нет поля article в вашей модели
                "price": float(item.prices[0][0]) if item.prices and item.prices[0] else None,
                "category": item.categories[0] if item.categories else "",
                "created_at": str(item.dates[0][0]) if item.dates and item.dates[0] else "",
                "updated_at": None,
            })
        return result

@router.post("", response_model=GoodsOut)
async def create_goods(goods: GoodsCreate, current_user: User = Depends(get_current_user)):
    async with async_session_maker() as session:
        new_item = await OzonDAO.add(
            user_id=current_user.id,
            cardnames=[goods.name],
            urls_of_cards=[],
            categories=[goods.category or ""],
            prices=[[int(goods.price) if goods.price else 0]],
            dates=[[""]],
            ratings=[[0]],
            reviews_counts=[[0]],
            descriptions=[goods.description or ""],
            feedbacks=[[]],
        )
        # Возвращаем в формате GoodsOut
        return {
            "id": new_item.id,
            "name": new_item.cardnames[0] if new_item.cardnames else "",
            "description": new_item.descriptions[0] if new_item.descriptions else "",
            "article": "",
            "price": float(new_item.prices[0][0]) if new_item.prices and new_item.prices[0] else None,
            "category": new_item.categories[0] if new_item.categories else "",
            "created_at": str(new_item.dates[0][0]) if new_item.dates and new_item.dates[0] else "",
            "updated_at": None,
        }