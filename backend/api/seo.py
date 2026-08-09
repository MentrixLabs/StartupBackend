from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from backend.core.dependencies import get_current_user
from db.user.models import User
from db.ozon.dao import SeoCompetitorDAO, SeoDataDAO
from db.db import async_session_maker
from backend.services.seo_service import generate_seo_for_goods
from backend.schemas.goods import SeoHistoryResponse

from typing import List

router = APIRouter()

class SeoRequest(BaseModel):
    goods_id: int

class SeoResponse(BaseModel):
    title: str
    description: str
    keywords: List[str]

@router.post("/generate", response_model=SeoResponse)
async def generate_seo(request: SeoRequest, current_user: User = Depends(get_current_user)):
    # Здесь вызвать ваш модуль ML (например, deepseekApi)
    # Пока заглушка
    result = await generate_seo_for_goods(goods_id=request.goods_id, user_id=current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Goods not found")
    return result

from typing import List

@router.get("/history/{goods_id}", response_model=SeoHistoryResponse)
async def get_seo_history(goods_id: int, current_user: User = Depends(get_current_user)):
    async with async_session_maker() as session:
        # Получаем сгенерированное SEO
        seo_data = await SeoDataDAO.find_one_or_none(goods_id=goods_id)
        # Получаем конкурентов
        competitors = await SeoCompetitorDAO.find_all(goods_id=goods_id)
        
        if not seo_data:
            # Если нет сгенерированного SEO, возвращаем пустую структуру
            return {
                "generated": None,
                "summary": None,
                "competitors": []
            }
        
        return {
            "generated": {
                "title": seo_data.generated_title,
                "description": seo_data.generated_description,
                "keywords": seo_data.generated_keywords,
            },
            "summary": seo_data.summary,
            "competitors": [
                {
                    "title": c.competitor_title,
                    "description": c.competitor_description,
                    "keywords": c.competitor_keywords,
                    "url": c.competitor_url,
                } for c in competitors
            ],
        }

@router.get("/{goods_id}/seo-history", response_model=SeoHistoryResponse)
async def get_goods_seo_history(goods_id: int, current_user: User = Depends(get_current_user)):
    async with async_session_maker() as session:
        # Проверяем, что товар принадлежит пользователю
        item = await OzonItemDAO.find_one_or_none(id=goods_id, user_id=current_user.id)
        if not item:
            raise HTTPException(status_code=404, detail="Товар не найден")
        
        # Получаем SEO-данные
        seo = await SeoDataDAO.find_one_or_none(goods_id=goods_id)
        competitors = await SeoCompetitorDAO.find_all(goods_id=goods_id)
        
        if not seo:
            # Если нет сгенерированного SEO, возвращаем пустую структуру
            return SeoHistoryResponse(generated=None, summary=None, competitors=[])
        
        return SeoHistoryResponse(
            generated={
                "title": seo.generated_title,
                "description": seo.generated_description,
                "keywords": seo.generated_keywords,
            },
            summary=seo.summary,
            competitors=[
                {
                    "title": c.competitor_title,
                    "description": c.competitor_description,
                    "keywords": c.competitor_keywords,
                    "url": c.competitor_url,
                } for c in competitors
            ]
        )