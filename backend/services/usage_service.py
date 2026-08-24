# backend/services/usage_service.py
from datetime import datetime, date
from typing import Dict, Any
from sqlalchemy import select, func
from fastapi import HTTPException
from db.db import async_session_maker
from db.ozon.models import OzonItem, SeoData, InfographicsData
from db.user.models import User
from backend.config.plans import get_plan_limits, get_plan_details

async def get_user_usage(user_id: int) -> Dict[str, Any]:
    """
    Возвращает текущее использование пользователем:
    - total_goods: общее количество товаров
    - seo_today: количество SEO-генераций сегодня
    - infographics_today: количество созданных инфографик (записей) сегодня
    - plan: текущий план пользователя
    """
    today = date.today()
    start_of_day = datetime.combine(today, datetime.min.time())

    async with async_session_maker() as session:
        # План пользователя
        user = await session.get(User, user_id)
        plan = user.plan if user else 'free'

        # Общее количество товаров
        total_goods_stmt = select(func.count()).select_from(OzonItem).where(OzonItem.user_id == user_id)
        total_goods = await session.scalar(total_goods_stmt) or 0

        # SEO сегодня (количество записей в SeoData за сегодня)
        seo_today_stmt = (
            select(func.count())
            .select_from(SeoData)
            .join(OzonItem, OzonItem.id == SeoData.goods_id)
            .where(OzonItem.user_id == user_id)
            .where(SeoData.created_at >= start_of_day)
        )
        seo_today = await session.scalar(seo_today_stmt) or 0

        # Инфографика сегодня (количество записей в InfographicsData за сегодня)
        infographics_today_stmt = (
            select(func.count())
            .select_from(InfographicsData)
            .join(OzonItem, OzonItem.id == InfographicsData.goods_id)
            .where(OzonItem.user_id == user_id)
            .where(InfographicsData.created_at >= start_of_day)
        )
        infographics_today = await session.scalar(infographics_today_stmt) or 0

    plan_details = get_plan_details(plan)
    return {
        "total_goods": total_goods,
        "seo_today": seo_today,
        "infographics_today": infographics_today,
        "plan": plan,
        "plan_details": plan_details,
    }

async def check_limits(user_id: int, action: str, extra: Dict[str, Any] = None) -> None:
    """
    Проверяет, не превышен ли лимит для указанного действия.
    Выбрасывает HTTPException 403 с сообщением о превышении.
    """
    usage = await get_user_usage(user_id)
    plan = usage["plan"]
    limits = get_plan_limits(plan)

    if action == "add_goods":
        max_goods = limits["max_goods"]
        if usage["total_goods"] >= max_goods:
            raise HTTPException(403, f"Превышен лимит товаров для тарифа '{plan}'. Максимум: {max_goods}.")
    elif action == "generate_seo":
        max_seo = limits["max_seo_per_day"]
        if usage["seo_today"] >= max_seo:
            raise HTTPException(403, f"Превышен дневной лимит SEO-генераций ({max_seo}) для тарифа '{plan}'.")
    elif action == "generate_infographics":
        max_inf = limits["max_infographics_per_day"]
        if usage["infographics_today"] >= max_inf:
            raise HTTPException(403, f"Превышен дневной лимит инфографики ({max_inf}) для тарифа '{plan}'.")
        # Проверка количества изображений в одном запросе (если передано)
        if extra and "count" in extra:
            max_per_req = limits.get("max_infographics_per_request", max_inf)
            if extra["count"] > max_per_req:
                raise HTTPException(403, f"За один запрос можно создать не более {max_per_req} изображений (ваш тариф '{plan}').")
    else:
        raise ValueError(f"Неизвестное действие: {action}")