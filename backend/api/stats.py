from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, text
from datetime import datetime, timedelta
import random
import hashlib
from typing import List, Dict, Any

from db.db import async_session_maker
from db.user.dao import UserDAO
from db.ozon.models import OzonItem, SeoData           # модель SEO-данных (у вас в db.ozon.models)
from backend.core.dependencies import get_current_user

router = APIRouter(prefix="/stats", tags=["stats"])

# Вспомогательная функция для получения сессии (как в auth.py)
async def get_async_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session


@router.get("/weekly-activity")
async def get_weekly_activity(
    current_user = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Возвращает количество SEO-генераций по дням за последние 7 дней.
    """
    today = datetime.utcnow().date()
    start_date = today - timedelta(days=6)
    
    # Группируем по дате (created_at::date) для SeoData, связанного с товарами пользователя
    stmt = (
        select(
            func.date(SeoData.created_at).label("day"),
            func.count().label("count")
        )
        .join(OzonItem, OzonItem.id == SeoData.goods_id)
        .where(OzonItem.user_id == current_user.id)
        .where(SeoData.created_at >= start_date)
        .group_by(func.date(SeoData.created_at))
        .order_by(func.date(SeoData.created_at))
    )
    result = await session.execute(stmt)
    rows = result.all()
    
    # Заполняем все 7 дней (если нет данных – 0)
    day_counts = {row.day: row.count for row in rows}
    week_days = []
    for i in range(7):
        d = start_date + timedelta(days=i)
        week_days.append({
            "day": d.strftime("%a"),  # Пн, Вт, ...
            "seo": day_counts.get(d, 0),
            "infographics": 0  # пока нет отдельной таблицы инфографики
        })
    return week_days


@router.get("/content-distribution")
async def get_content_distribution(
    current_user = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Общее количество SEO, инфографики и отчётов.
    """
    # Количество SEO (записей в SeoData)
    seo_count_stmt = select(func.count()).select_from(SeoData).join(OzonItem).where(OzonItem.user_id == current_user.id)
    seo_count = await session.scalar(seo_count_stmt) or 0
    
    # Количество инфографики – сумма длин массивов main_imgs и desc_imgs
    total_images_stmt = select(
        func.sum(
            func.coalesce(func.array_length(OzonItem.main_imgs, 1), 0) +
            func.coalesce(func.array_length(OzonItem.desc_imgs, 1), 0)
        )
    ).where(OzonItem.user_id == current_user.id)
    infographics_count = await session.scalar(total_images_stmt) or 0
    
    # Отчёты – пока заглушка (можно добавить таблицу Reports позже)
    reports_count = 0
    
    return {
        "seo": seo_count,
        "infographics": infographics_count,
        "reports": reports_count
    }


@router.get("/recommendation")
async def get_recommendation(
    current_user = Depends(get_current_user),
):
    """
    Генерирует планку на неделю: цели по SEO и инфографике.
    """
    week_number = datetime.utcnow().isocalendar()[1]
    seed = f"{current_user.id}-{week_number}"
    hash_val = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    random.seed(hash_val)
    
    target_seo = random.randint(3, 8)
    target_infographics = random.randint(2, 6)
    return {
        "target_seo": target_seo,
        "target_infographics": target_infographics
    }