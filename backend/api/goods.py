from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from db.db import async_session_maker
from db.ozon.dao import OzonItemDAO
from backend.schemas.goods import GoodsCreate, GoodsUpdate, GoodsOut
from backend.core.dependencies import get_current_user
from db.user.models import User

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
        new_item = await OzonItemDAO.add(
            user_id=current_user.id,
            cardname=goods.name,
            description=goods.description or "",
            url=goods.url,
        )
        if new_item is None:
            raise HTTPException(status_code=500, detail="Ошибка создания товара")
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