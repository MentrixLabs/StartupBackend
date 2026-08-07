from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from backend.core.dependencies import get_current_user
from db.user.models import User
from backend.services.seo_service import generate_seo_for_goods

router = APIRouter()

class SeoRequest(BaseModel):
    goods_id: int

class SeoResponse(BaseModel):
    title: str
    description: str
    keywords: List[str]

@router.post("/generate", response_model=SeoResponse)
async def generate_ig(request: SeoRequest, current_user: User = Depends(get_current_user)):
    # Здесь вызвать ваш модуль ML (например, deepseekApi)
    # Пока заглушка
    result = await generate_seo_for_goods(goods_id=request.goods_id, user_id=current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Goods not found")
    return result