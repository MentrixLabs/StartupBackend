# backend/api/infographics.py (полностью)

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from backend.core.dependencies import get_current_user
from db.user.models import User
from backend.services.infographics_service import generate_infographics
from backend.services.image_enhancement_service import enhance_goods_images
from db.ozon.dao import InfographicsDataDAO
from db.db import async_session_maker
from backend.services.usage_service import check_limits


router = APIRouter()

class InfographicsRequest(BaseModel):
    goods_id: int
    count: Optional[int] = 4

class InfographicsResponse(BaseModel):
    images: List[str]

@router.post("/generate", response_model=InfographicsResponse)
async def generate_infographics_router(
    request: InfographicsRequest,
    current_user: User = Depends(get_current_user)
):
    await check_limits(current_user.id, "generate_infographics", extra={"count": request.count})
    try:
        images = await generate_infographics(
            goods_id=request.goods_id,
            user_id=current_user.id,
            count=request.count
        )
        return InfographicsResponse(images=images)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка генерации инфографики: {str(e)}")

@router.post("/enhance", response_model=InfographicsResponse)
async def enhance_infographics_router(
    request: InfographicsRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Улучшает существующие изображения товара (коллаж + текст).
    Проверяет лимиты на количество инфографик в день.
    """
    # Проверка лимитов (count=1, так как улучшаем одно изображение)
    await check_limits(current_user.id, "generate_infographics", extra={"count": 1})
    
    # Вызов сервиса улучшения
    result = await enhance_goods_images(request.goods_id, current_user.id)
    return result

@router.get("/{goods_id}")
async def get_infographics_data(
    goods_id: int,
    current_user: User = Depends(get_current_user)
):
    """Получить сохранённые данные инфографики для товара."""
    async with async_session_maker() as session:
        data = await InfographicsDataDAO.find_one_or_none(goods_id=goods_id)
        if not data:
            return {"generated_images": [], "enhanced_images": []}
        return {
            "generated_images": data.generated_images or [],
            "enhanced_images": data.enhanced_images or []
        }