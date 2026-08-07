from fastapi import APIRouter, Depends, HTTPException
from backend.core.dependencies import get_current_user
from db.user.models import User
from backend.services.report_service import generate_report_data

router = APIRouter()

@router.get("/generate/{goods_id}")
async def generate_report(goods_id: int, current_user: User = Depends(get_current_user)):
    """
    Генерирует данные отчёта по прогнозу остатков для товара (JSON).
    """
    data = await generate_report_data(goods_id, current_user.id)
    return data