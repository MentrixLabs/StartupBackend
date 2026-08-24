# backend/api/user.py
from fastapi import APIRouter, Depends
from backend.core.dependencies import get_current_user
from db.user.models import User
from backend.services.usage_service import get_user_usage

router = APIRouter(prefix="/user", tags=["user"])

@router.get("/status")
async def get_user_status(current_user: User = Depends(get_current_user)):
    """
    Возвращает статус пользователя:
    - план,
    - использование (товары, SEO сегодня, инфографика сегодня),
    - детали плана (лимиты, доступные фичи).
    """
    usage = await get_user_usage(current_user.id)
    return usage