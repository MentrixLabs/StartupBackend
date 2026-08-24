# backend/services/report_service.py
import json
import logging
import re
from datetime import date, timedelta, datetime
from typing import Dict, Any, List, Optional
from fastapi import HTTPException
from sqlalchemy import select, func, and_, text, or_, desc
from db.db import async_session_maker
from db.ozon.dao import OzonItemDAO, OzonItemHistoryDAO, OzonItemCategoryDAO, InfographicsDataDAO, SeoDataDAO
from db.ozon.models import Report
from backend.utils.GigaChatAPI import GigaChatModel
from config import settings
from backend.config.plans import get_plan_details

logger = logging.getLogger(__name__)

# Инициализация GigaChat (используем тот же экземпляр, что и для SEO)
gigachat_model = GigaChatModel(
    credentials=settings.SBER_AUTHORIZATION_KEY,
    scope="GIGACHAT_API_PERS"
)

def serialize_dates(obj):
    if isinstance(obj, dict):
        return {k: serialize_dates(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_dates(item) for item in obj]
    elif hasattr(obj, 'isoformat'):  # date, datetime
        return obj.isoformat()
    else:
        return obj


async def generate_report_data(goods_id: int, user_id: int) -> Dict[str, Any]:
    """
    Генерирует расширенный отчёт по товару с прогнозами и рекомендациями.
    Использует реальные данные из БД и GigaChat для построения прогнозов.
    """
    # 1. Получаем данные товара и историю
    async with async_session_maker() as session:
        goods = await OzonItemDAO.find_one_or_none(id=goods_id, user_id=user_id)
        if not goods:
            raise HTTPException(status_code=404, detail="Товар не найден или доступ запрещён")

        # Категория
        categories = await OzonItemCategoryDAO.find_all(item_id=goods.id)
        category = categories[0].category if categories else ""

        # История цен, рейтингов, отзывов
        history = await OzonItemHistoryDAO.find_all(item_id=goods.id)
        # Сортируем по дате
        history = sorted(history, key=lambda h: h.record_date)

        fbs_counts = [h.fbs_count for h in history if h.fbs_count is not None]
        current_stock = fbs_counts[-1] if fbs_counts else None

        # Подготовка данных для промпта
        name = goods.cardname or "Товар"
        description = goods.description or ""
        brand = goods.brand or ""
        provider = goods.provider or ""
        original_price = goods.original_price
        currency = goods.currency or "RUB"

        # Список дат, цен, рейтингов, отзывов
        dates = [h.record_date.isoformat() for h in history] if history else []
        prices = [h.price for h in history if h.price is not None] if history else []
        ratings = [h.rating for h in history if h.rating is not None] if history else []
        reviews_counts = [h.reviews_count for h in history if h.reviews_count is not None] if history else []

        infographics = await InfographicsDataDAO.find_one_or_none(goods_id=goods.id)
        has_generated = infographics and infographics.generated_images and len(infographics.generated_images) > 0
        has_enhanced = infographics and infographics.enhanced_images and len(infographics.enhanced_images) > 0

        seo_generated = await SeoDataDAO.find_all(goods_id=goods.id)
        if seo_generated:
            seo_generated = seo_generated[-1]

            generated_title = seo_generated.generated_title
            generated_description = seo_generated.generated_description
            generated_keywords = seo_generated.generated_keywords
            summary = seo_generated.summary
            # Новые поля
            advertising_spend_ratio = seo_generated.advertising_spend_ratio  # массив [old, new]
            leads = seo_generated.leads                   # массив [old, new]
            ctr = seo_generated.ctr                     # массив [old, new]
            adv_growth = advertising_spend_ratio[1] / advertising_spend_ratio[0] if advertising_spend_ratio[0] != 0 else 1.0
            leads_growth = leads[1] / leads[0] if leads[0] != 0 else 1.0
            ctr_growth = ctr[1] / ctr[0] if ctr[0] != 0 else 1.0
        else:
            generated_title = "Нет данных"
            generated_description = "Нет данных"
            generated_keywords = "Нет данных"
            summary = "Нет данных"
            adv_growth = 1.0
            leads_growth = 1.0
            ctr_growth = 1.0

        # Добавить в промпт информацию о наличии инфографики
        infographics_info = "Есть сгенерированные изображения" if has_generated else "Нет сгенерированных изображений"
        if has_enhanced:
            infographics_info += ", есть улучшенные изображения (коллаж с текстом)"
        else:
            infographics_info += ", улучшенные изображения отсутствуют"
    # 2. Формируем промпт для GigaChat
    instructions = "Ты — аналитик маркетплейса с 20-летним опытом в e-commerce и цифровом маркетинге. Проанализируй данные товара и сгенерируй прогнозы на 30 дней."
    prompt = f"""
    {instructions}

    Данные товара:
    - Название: {name}
    - Категория: {category}
    - Бренд: {brand}
    - Поставщик: {provider}
    - Описание: {description[:300]}
    - Текущая цена: {original_price} {currency}
    - История цен (дата, цена): {list(zip(dates, prices)) if prices else 'Нет'}
    - История рейтингов: {list(zip(dates, ratings)) if ratings else 'Нет'}
    - История отзывов: {list(zip(dates, reviews_counts)) if reviews_counts else 'Нет'}
    - Инфографика: {infographics_info}
    - Текущий остаток на складе: {current_stock if current_stock is not None else 'Неизвестно'}
    - История остатков: {list(zip(dates, fbs_counts)) if fbs_counts else 'Нет'}
    - Новое сгенерированное SEO название товара: {generated_title}
    - Новое сгенерированное SEO описание товара: {generated_description}
    - Новые сгенерированные SEO ключевые слова товара: {generated_keywords}
    - Новая сгенерированная сводка по SEO товара: {summary}
    - Прогнозируемое увеличение доли рекламных расходлов за счёт сгенерированного SEO и инфографики товара: {adv_growth}
    - Прогнозируемое увеличение количества лидов за счёт сгенерированного SEO и инфографики товара: {leads_growth}
    - Прогнозируемое увеличение CTR за счёт сгенерированного SEO и инфографики товара: {ctr_growth}

    Твоя задача – построить прогнозы и дать рекомендации, используя экономические и маркетинговые концепции.
    Если нет данных по SEO - скажи, что пользователю необходимо сгенерировать хотя бы одно SEO для подробной отчётности

    Сгенерируй JSON-ответ строго по следующей схеме. Все поля обязательны.
    Если данных недостаточно, используй разумные приближения на основе имеющейся информации.

    {{
    "days_to_out_of_stock": "строка – прогноз, когда товар закончится (например, 'Товар закончится через 15 дней' или 'Недостаточно данных')",
    "price_dynamic": "строка – описание динамики цены на 30 дней (рост, падение, стабильность) с кратким обоснованием",
    "forecast": [
        {{"date": "YYYY-MM-DD", "price": число, "demand": число, "stock": число}}
    ], // 30 записей, начиная с сегодня
    "recommended_price": число,
    "revenue_forecast": [
        {{"date": "YYYY-MM-DD", "revenue": число}}
    ], // 30 записей
    "key_metrics": {{
        "avg_price": число,
        "max_price": число,
        "min_price": число,
        "volatility": число
    }},
    "advertising_spend_ratio_forecast": [
        {{"date": "YYYY-MM-DD", "value": [процент увеличения показателя относительно текущего показателя, процент увеличения показателя относительно текущего показателя, процент увеличения показателя относительно текущего показателя]}}
    ], // 30 записей, массив из трёх значений: [следование рекомендациям, бездействие, пересечение]
    "leads_forecast": [
        {{"date": "YYYY-MM-DD", "value": [процент увеличения показателя относительно текущего показателя, процент увеличения показателя относительно текущего показателя, процент увеличения показателя относительно текущего показателя]}}
    ], // 30 записей, аналогично
    "ctr_forecast": [
        {{"date": "YYYY-MM-DD", "value": [процент увеличения показателя относительно текущего показателя, процент увеличения показателя относительно текущего показателя, процент увеличения показателя относительно текущего показателя]}}
    ], // 30 записей, аналогично
    "advertising_spend_ratio_description": "строка – развёрнутое описание (на русском, но с использованием английских научных терминов), почему качественные SEO и инфографика снижают долю рекламных расходов по сравнению с текущей карточкой. Объясни механизм: улучшение органической видимости -> рост кликабельности -> снижение зависимости от платного трафика. Подчеркни, что в рамках недельного AB-тестирования важно следовать предложенным планкам для получения статистически значимых результатов.",
    "leads_description": "строка – аналогично, но про лиды: почему улучшенный контент увеличивает количество целевых лидов. Используй термины: conversion rate, lead quality, funnel efficiency, A/B testing significance.",
    "ctr_description": "строка – аналогично, но про CTR: почему оптимизированные заголовки и описания повышают кликабельность. Упомяни: click-through rate, ad relevance, user engagement, attribution modelling.",
    "keywords": ["ключевое слово1", "ключевое слово2", ...],
    "recommendations": "текст рекомендаций по улучшению карточки товара (SEO, описание, изображения, ценообразование)"
    }}

    Важно: все прогнозные массивы должны содержать ровно 30 записей, начиная с сегодняшнего дня (date = YYYY-MM-DD).
    Если история цен или остатков отсутствует, экстраполируй данные на основе имеющихся трендов или используй средние значения.

    Ответ должен быть только JSON, без лишнего текста.
    """
    prompt += "\n\nОТВЕТ ДОЛЖЕН БЫТЬ ТОЛЬКО JSON, БЕЗ ЛИШНИХ ПОЯСНЕНИЙ И БЕЗ МАРКДАУН-РАЗМЕТКИ (без ```json)."
    try:
        response_text = await gigachat_model.getResponseByPromt(prompt)
        clean_json = extract_json_from_response(response_text)
        try:
            result = json.loads(clean_json)
        except json.JSONDecodeError as e:
            logger.error(f"Не удалось распарсить JSON из ответа: {e}\nОтвет: {response_text[:500]}")
            return _build_fallback_report(...)

        required_fields = (
            "days_to_out_of_stock", "price_dynamic", "forecast", "recommended_price",
            "revenue_forecast", "key_metrics",
            "advertising_spend_ratio_forecast", "leads_forecast", "ctr_forecast",
            "advertising_spend_ratio_description", "leads_description", "ctr_description",
            "keywords", "recommendations"
        )
        if not all(field in result for field in required_fields):
            missing = [f for f in required_fields if f not in result]
            raise ValueError(f"Missing fields: {missing}")

        # Преобразуем типы (при необходимости)
        # forecast и revenue_forecast должны быть списками
        forecast = result["forecast"]
        revenue_forecast = result["revenue_forecast"]
        # Если прогнозов меньше 30, дополним последним значением
        today = date.today()
        while len(forecast) < 30:
            last = forecast[-1] if forecast else {"date": today.isoformat(), "price": 0, "demand": 0, "stock": 0}
            next_date = date.fromisoformat(last["date"]) + timedelta(days=1)
            forecast.append({
                "date": next_date.isoformat(),
                "price": last["price"],
                "demand": last["demand"],
                "stock": last["stock"]
            })
        while len(revenue_forecast) < 30:
            last = revenue_forecast[-1] if revenue_forecast else {"date": today.isoformat(), "revenue": 0}
            next_date = date.fromisoformat(last["date"]) + timedelta(days=1)
            revenue_forecast.append({"date": next_date.isoformat(), "revenue": last["revenue"]})

        # Обрезаем до 30 записей
        result["forecast"] = forecast[:30]
        result["revenue_forecast"] = revenue_forecast[:30]

        # Добавляем goods_id
        result["goods_id"] = goods_id

        result = serialize_dates(result)

        return result

    except Exception as e:
        logger.error(f"Ошибка при генерации отчёта через GigaChat: {e}", exc_info=True)
        # Fallback – возвращаем структуру с заглушками
        return _build_fallback_report(goods_id, name, category, prices, ratings, reviews_counts)


def _build_fallback_report(goods_id: int, name: str, category: str, prices: List[float], ratings: List[float], reviews_counts: List[int]) -> Dict[str, Any]:
    today = date.today()
    base_price = prices[-1] if prices else 1000
    base_demand = 5
    forecast = []
    revenue = []
    for i in range(30):
        d = today + timedelta(days=i)
        price = base_price + i * 5
        demand = base_demand + i * 0.5
        forecast.append({"date": d.isoformat(), "price": price, "demand": demand, "stock": max(0, 100 - i * 3)})
        revenue.append({"date": d.isoformat(), "revenue": price * demand})

    return {
        "goods_id": goods_id,
        "days_to_out_of_stock": "Недостаточно данных для прогноза",
        "price_dynamic": "Цена стабильна",
        "forecast": forecast,
        "recommended_price": base_price * 1.05,
        "revenue_forecast": revenue,
        "key_metrics": {
            "avg_price": sum(prices) / len(prices) if prices else base_price,
            "max_price": max(prices) if prices else base_price,
            "min_price": min(prices) if prices else base_price,
            "volatility": 0
        },
        "advertising_spend_ratio_forecast": [{"date": (today + timedelta(days=i)).isoformat(), "value": [0.0, 0.0, 0.0]} for i in range(30)],
        "leads_forecast": [{"date": (today + timedelta(days=i)).isoformat(), "value": [0.0, 0.0, 0.0]} for i in range(30)],
        "ctr_forecast": [{"date": (today + timedelta(days=i)).isoformat(), "value": [0.0, 0.0, 0.0]} for i in range(30)],
        "advertising_spend_ratio_description": (
            "Качественная SEO-оптимизация и профессиональная инфографика снижают долю рекламных расходов (ad spend ratio) "
            "за счёт повышения органической видимости и конверсии. Это подтверждается концепцией 'attribution modelling', "
            "где улучшение качества контента увеличивает долю бесплатного трафика. В рамках недельного A/B-тестирования "
            "следование планкам позволит получить статистически значимые данные о снижении ДРР."
        ),
        "leads_description": (
            "Оптимизированные заголовки, описания и визуалы повышают conversion rate и качество лидов (lead quality). "
            "Эффект объясняется улучшением соответствия запросам пользователей и повышением доверия к карточке. "
            "A/B-тест с предложенными улучшениями покажет рост лидов на 15–25% при сохранении бюджета."
        ),
        "ctr_description": (
            "Повышение click-through rate (CTR) достигается за счёт релевантных заголовков и привлекательных мета-описаний. "
            "Это снижает стоимость клика (CPC) и улучшает общую эффективность рекламной кампании. "
            "В условиях A/B-тестирования важно придерживаться планок, чтобы оценить реальный прирост CTR без искажающих факторов."
        ),
        "keywords": [f"Купить {name}", f"{name} цена", "лучшая цена"],
        "recommendations": "Попробуйте улучшить карточку товара для повышения конверсии."
    }


async def can_generate_report(goods_id: int, user_id: int, plan: str) -> bool:
    """
    Проверяет, можно ли создать новый отчёт для товара.
    Разрешено не чаще, чем указано в плане (cooldown).
    """
    cooldown = get_plan_details(plan).get("report_cooldown_days", 7)
    async with async_session_maker() as session:
        stmt = (
            select(Report)
            .where(Report.goods_id == goods_id, Report.user_id == user_id)
            .order_by(desc(Report.created_at))
            .limit(1)
        )
        result = await session.execute(stmt)
        last = result.scalar_one_or_none()
        if not last:
            return True
        delta = datetime.utcnow() - last.created_at
        return delta.days >= cooldown

def extract_json_from_response(text: str) -> str:
    """
    Пытается извлечь JSON из текста ответа GigaChat.
    Ищет блок ```json ... ``` или любой объект/массив в фигурных/квадратных скобках.
    """
    # Ищем блок с кодом JSON
    match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        return match.group(1)

    # Ищем первый полный JSON-объект
    match = re.search(r'(\{.*\})', text, re.DOTALL)
    if match:
        return match.group(1)

    # Если ничего не найдено, возвращаем исходный текст (он может быть JSON, но без форматирования)
    return text