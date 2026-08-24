from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from backend.core.dependencies import get_current_user
from db.user.models import User
from db.ozon.dao import SeoCompetitorDAO, SeoDataDAO
from db.db import async_session_maker
from backend.services.seo_service import generate_seo_for_goods
from backend.schemas.goods import SeoHistoryResponse
from backend.services.usage_service import check_limits

from typing import List

router = APIRouter()

class SeoRequest(BaseModel):
    goods_id: int

class SeoResponse(BaseModel):
    title: str
    description: str
    keywords: List[str]
    advertising_spend_ratio: List[float]
    leads: List[float]
    CTR: List[float]

@router.post("/generate", response_model=SeoResponse)
async def generate_seo(request: SeoRequest, current_user: User = Depends(get_current_user)):
    await check_limits(current_user.id, "generate_seo")
    result = await generate_seo_for_goods(goods_id=request.goods_id, user_id=current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Goods not found")
    return result

from typing import List

@router.get("/history/{goods_id}", response_model=SeoHistoryResponse)
async def get_seo_history(goods_id: int, current_user: User = Depends(get_current_user)):
    async with async_session_maker() as session:
        seo_data = await SeoDataDAO.find_one_or_none(goods_id=goods_id)
        competitors = await SeoCompetitorDAO.find_all(goods_id=goods_id)

        if not seo_data:
            return {"generated": None, "summary": None, "competitors": []}

        return {
            "generated": {
                "title": seo_data.generated_title,
                "description": seo_data.generated_description,
                "keywords": seo_data.generated_keywords,
                "advertising_spend_ratio": seo_data.advertising_spend_ratio,
                "leads": seo_data.leads,
                "CTR": seo_data.ctr,
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