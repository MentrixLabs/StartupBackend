from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging
import io

from backend.core.dependencies import get_current_user
from db.user.models import User
from db.ozon.dao import ReportDAO, OzonItemDAO
from db.db import async_session_maker
from backend.services.report_service import generate_report_data

logger = logging.getLogger(__name__)

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
    all_reports = await ReportDAO.find_all(user_id=current_user.id)
    total = len(all_reports) if all_reports else 0

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


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Получить данные одного отчёта для просмотра."""
    report = await ReportDAO.find_one_or_none(id=report_id, user_id=current_user.id)
    if not report:
        raise HTTPException(status_code=404, detail="Отчёт не найден или доступ запрещён")
    return ReportResponse(
        id=report.id,
        goods_id=report.goods_id,
        created_at=report.created_at,
        seo_text=report.seo_text,
        infographics=report.infographics or [],
        forecast_data=report.forecast_data or {}
    )


@router.post("/generate", response_model=ReportResponse)
async def generate_report(
    req: ReportCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    try:
        goods = await OzonItemDAO.find_one_or_none(id=req.goods_id, user_id=current_user.id)
        if not goods:
            raise HTTPException(404, "Товар не найден или доступ запрещён")

        forecast_data = await generate_report_data(req.goods_id, current_user.id)

        seo_text = goods.description or ""
        infographics = (goods.main_imgs or []) + (goods.desc_imgs or [])

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
    report = await ReportDAO.find_one_or_none(id=report_id, user_id=current_user.id)
    if not report:
        raise HTTPException(404, "Отчёт не найден или доступ запрещён")
    await ReportDAO.delete(id=report_id)
    return None


@router.get("/{report_id}/download")
async def download_report_pdf(
    report_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Скачать отчёт в формате PDF."""
    report = await ReportDAO.find_one_or_none(id=report_id, user_id=current_user.id)
    if not report:
        raise HTTPException(404, "Отчёт не найден или доступ запрещён")

    # Получаем данные товара для названия
    goods = await OzonItemDAO.find_one_or_none(id=report.goods_id, user_id=current_user.id)
    goods_name = goods.cardname if goods else "Товар"

    forecast_data = report.forecast_data or {}

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                rightMargin=2*cm, leftMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Title'],
            fontSize=16,
            alignment=TA_CENTER,
            spaceAfter=20
        )
        heading_style = ParagraphStyle(
            'HeadingStyle',
            parent=styles['Heading2'],
            fontSize=12,
            spaceAfter=10
        )
        body_style = ParagraphStyle(
            'BodyStyle',
            parent=styles['BodyText'],
            fontSize=10,
            spaceAfter=6
        )

        elements = []

        # Заголовок
        elements.append(Paragraph(f"Отчёт по товару: {goods_name}", title_style))
        elements.append(Paragraph(f"Дата: {report.created_at.strftime('%d.%m.%Y %H:%M')}", body_style))
        elements.append(Spacer(1, 0.5*cm))

        # Прогноз остатков
        elements.append(Paragraph("Прогноз остатков", heading_style))
        elements.append(Paragraph(forecast_data.get("days_to_out_of_stock", "Нет данных"), body_style))
        elements.append(Spacer(1, 0.3*cm))

        # Динамика цены
        elements.append(Paragraph("Динамика цены", heading_style))
        elements.append(Paragraph(forecast_data.get("price_dynamic", "Нет данных"), body_style))
        elements.append(Spacer(1, 0.3*cm))

        # Рекомендуемая цена
        rec_price = forecast_data.get("recommended_price")
        if rec_price is not None:
            elements.append(Paragraph("Рекомендуемая цена", heading_style))
            elements.append(Paragraph(f"{rec_price:.2f} RUB", body_style))
            elements.append(Spacer(1, 0.3*cm))

        # Ключевые метрики
        metrics = forecast_data.get("key_metrics", {})
        if metrics:
            elements.append(Paragraph("Ключевые метрики", heading_style))
            data = [
                ["Средняя цена", f"{metrics.get('avg_price', '—')}"],
                ["Максимальная цена", f"{metrics.get('max_price', '—')}"],
                ["Минимальная цена", f"{metrics.get('min_price', '—')}"],
                ["Волатильность", f"{metrics.get('volatility', '—')}"]
            ]
            table = Table(data, colWidths=[4*cm, 6*cm])
            table.setStyle(TableStyle([
                ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
                ('FONTSIZE', (0,0), (-1,-1), 10),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('BACKGROUND', (0,0), (0,-1), colors.lightgrey),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 0.5*cm))

        # Рекомендации
        recommendations = forecast_data.get("recommendations", "Нет рекомендаций")
        if recommendations:
            elements.append(Paragraph("Рекомендации", heading_style))
            elements.append(Paragraph(recommendations, body_style))
            elements.append(Spacer(1, 0.3*cm))

        # Прогноз по дням (если есть)
        forecast = forecast_data.get("forecast", [])
        if forecast:
            elements.append(Paragraph("Прогноз по дням (первые 10)", heading_style))
            table_data = [["Дата", "Цена", "Спрос", "Остаток"]]
            for item in forecast[:10]:
                table_data.append([
                    item.get("date", ""),
                    f"{item.get('price', 0):.0f}",
                    f"{item.get('demand', 0):.0f}",
                    f"{item.get('stock', 0):.0f}"
                ])
            table = Table(table_data, colWidths=[2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm])
            table.setStyle(TableStyle([
                ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
                ('FONTSIZE', (0,0), (-1,-1), 8),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]))
            elements.append(table)

        doc.build(elements)
        buffer.seek(0)

        from fastapi.responses import Response
        return Response(
            content=buffer.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="report_{report_id}.pdf"'}
        )

    except ImportError:
        logger.warning("reportlab not installed – returning JSON instead of PDF")
        return {
            "message": "PDF generation not available (install reportlab)",
            "data": {
                "id": report.id,
                "created_at": report.created_at,
                "forecast": forecast_data
            }
        }
    except Exception as e:
        logger.error(f"PDF generation failed: {e}", exc_info=True)
        raise HTTPException(500, f"Ошибка генерации PDF: {str(e)}")