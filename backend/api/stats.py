from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, text
from datetime import datetime, timedelta
import random
import hashlib
from typing import List, Dict, Any
import logging

from db.db import async_session_maker
from db.user.dao import UserDAO
from db.ozon.models import OzonItem, SeoData, InfographicsData           # модель SEO-данных (у вас в db.ozon.models)
from backend.core.dependencies import get_current_user

router = APIRouter(prefix="/stats", tags=["stats"])
logger = logging.getLogger(__name__)

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
    
    # Явное соединение SeoData -> OzonItem через goods_id
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
    
    # Заполняем все 7 дней
    day_counts = {row.day: row.count for row in rows}
    week_days = []
    for i in range(7):
        d = start_date + timedelta(days=i)
        week_days.append({
            "day": d.strftime("%a"),  # Mon, Tue, ...
            "seo": day_counts.get(d, 0),
            "infographics": 0  # пока нет отдельной инфографики по дням
        })
    logger.info(f"Weekly activity for user {current_user.id}: {week_days}")
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
    seo_count_stmt = (
        select(func.count())
        .select_from(SeoData)
        .join(OzonItem, OzonItem.id == SeoData.goods_id)
        .where(OzonItem.user_id == current_user.id)
    )
    seo_count = await session.scalar(seo_count_stmt) or 0

    # Количество товаров, у которых есть сгенерированная или улучшенная инфографика
    # (т.е. запись в infographics_data с непустым массивом generated_images или enhanced_images)
    infographics_count_stmt = (
        select(func.count())
        .select_from(InfographicsData)
        .join(OzonItem, OzonItem.id == InfographicsData.goods_id)
        .where(OzonItem.user_id == current_user.id)
        .where(
            or_(
                InfographicsData.generated_images != None,
                InfographicsData.enhanced_images != None
            )
        )
    )
    infographics_count = await session.scalar(infographics_count_stmt) or 0

    # Отчёты – пока заглушка
    reports_count = 0

    logger.info(f"Content distribution for user {current_user.id}: SEO={seo_count}, Infographics={infographics_count}, Reports={reports_count}")
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