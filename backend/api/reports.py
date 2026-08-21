from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from backend.core.dependencies import get_current_user
from db.user.models import User
from db.ozon.dao import ReportDAO, OzonItemDAO
from db.db import async_session_maker
from backend.services.report_service import generate_report_data

from logging import Logger

logger = Logger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])

# ---- Схемы ----
class ReportCreateRequest(BaseModel):
    goods_id: int

class ReportResponse(BaseModel):
    id: int
    goods_id: int
    created_at: datetime
    seo_text: Optional[str] = None
    infographics: Optional[List[str]] = None
    forecast_data: Optional[dict] = None

class PaginatedReportsResponse(BaseModel):
    items: List[ReportResponse]
    total: int
    page: int
    size: int
    pages: int

# ---- Вспомогательная функция для сессии ----
async def get_async_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session

# ---- Эндпоинты ----
@router.get("", response_model=PaginatedReportsResponse)
async def get_reports(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Получить список отчётов пользователя с пагинацией."""
    # Подсчёт общего количества
    all_reports = await ReportDAO.find_all(user_id=current_user.id)
    total = len(all_reports) if all_reports else 0

    # Сортировка по убыванию created_at (новые сверху)
    if all_reports:
        all_reports.sort(key=lambda r: r.created_at, reverse=True)
        start = (page - 1) * size
        end = start + size
        paginated = all_reports[start:end]
    else:
        paginated = []

    items = []
    for r in paginated:
        items.append(ReportResponse(
            id=r.id,
            goods_id=r.goods_id,
            created_at=r.created_at,
            seo_text=r.seo_text,
            infographics=r.infographics or [],
            forecast_data=r.forecast_data or {}
        ))

    return PaginatedReportsResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size if total > 0 else 0
    )


@router.post("/generate", response_model=ReportResponse)
async def generate_report(
    req: ReportCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Сгенерировать отчёт для указанного товара и сохранить в БД.
    """
    try:
        # Проверяем, что товар принадлежит пользователю
        goods = await OzonItemDAO.find_one_or_none(id=req.goods_id, user_id=current_user.id)
        if not goods:
            raise HTTPException(status_code=404, detail="Товар не найден или доступ запрещён")

        # Генерируем данные отчёта
        try:
            forecast_data = await generate_report_data(req.goods_id, current_user.id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ошибка генерации отчёта: {str(e)}")

        # Подготавливаем SEO-текст и инфографику из данных товара (можно расширить)
        seo_text = goods.description or ""
        infographics = (goods.main_imgs or []) + (goods.desc_imgs or [])

        # Создаём запись отчёта
        new_report = await ReportDAO.add(
            goods_id=req.goods_id,
            user_id=current_user.id,
            seo_text=seo_text,
            infographics=infographics,
            forecast_data=forecast_data
        )

        return ReportResponse(
            id=new_report.id,
            goods_id=new_report.goods_id,
            created_at=new_report.created_at,
            seo_text=new_report.seo_text,
            infographics=new_report.infographics or [],
            forecast_data=new_report.forecast_data or {}
        )
    except Exception as e:
        logger.error(f"Report generation failed: {e}", exc_info=True)
        raise HTTPException(500, f"Ошибка генерации отчёта: {str(e)}")

@router.delete("/{report_id}", status_code=204)
async def delete_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Удалить отчёт по ID (только если он принадлежит пользователю)."""
    report = await ReportDAO.find_one_or_none(id=report_id, user_id=current_user.id)
    if not report:
        raise HTTPException(status_code=404, detail="Отчёт не найден или доступ запрещён")
    await ReportDAO.delete(id=report_id)
    return None


@router.get("/download/{report_id}")
async def download_report_pdf(
    report_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Заглушка для скачивания отчёта в PDF (пока возвращает JSON)."""
    report = await ReportDAO.find_one_or_none(id=report_id, user_id=current_user.id)
    if not report:
        raise HTTPException(status_code=404, detail="Отчёт не найден или доступ запрещён")
    # Здесь можно сгенерировать PDF, но пока вернём JSON с данными отчёта
    return {
        "message": "Скачивание PDF пока не реализовано. Вот данные отчёта:",
        "data": {
            "id": report.id,
            "created_at": report.created_at,
            "forecast": report.forecast_data
        }
    }