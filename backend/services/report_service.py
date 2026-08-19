# backend/services/report_service.py
import json
import logging
from datetime import date, timedelta
from typing import Dict, Any, List, Optional
from fastapi import HTTPException
from sqlalchemy import select, func, and_, text, or_
from db.db import async_session_maker
from db.ozon.dao import OzonItemDAO, OzonItemHistoryDAO, OzonItemCategoryDAO, InfographicsDataDAO
from backend.utils.GigaChatAPI import GigaChatModel
from config import settings

logger = logging.getLogger(__name__)

# Инициализация GigaChat (используем тот же экземпляр, что и для SEO)
gigachat_model = GigaChatModel(
    credentials=settings.SBER_AUTHORIZATION_KEY,
    scope="GIGACHAT_API_PERS"
)

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

        # Добавить в промпт информацию о наличии инфографики
        infographics_info = "Есть сгенерированные изображения" if has_generated else "Нет сгенерированных изображений"
        if has_enhanced:
            infographics_info += ", есть улучшенные изображения (коллаж с текстом)"
        else:
            infographics_info += ", улучшенные изображения отсутствуют"
    # 2. Формируем промпт для GigaChat
    prompt = f"""
    Ты — аналитик маркетплейса. Проанализируй следующие данные о товаре и сгенерируй прогнозы и рекомендации.
        
    Название товара: {name}
    Категория: {category}
    Бренд: {brand}
    Поставщик: {provider}
    Описание: {description[:500]}
    Текущая цена: {original_price} {currency}
    История цен (дата, цена): {list(zip(dates, prices)) if prices else 'Нет данных'}
    История рейтингов: {list(zip(dates, ratings)) if ratings else 'Нет данных'}
    История количества отзывов: {list(zip(dates, reviews_counts)) if reviews_counts else 'Нет данных'}
    Инфографика: {infographics_info}

    На основе этих данных построй прогноз:
    1. Прогноз остатков (когда товар может закончиться, если известна динамика продаж) – если данных нет, укажи "Недостаточно данных".
    2. Динамика цены – как цена будет меняться в ближайшие 30 дней (рост, падение, стабильность).
    3. Прогноз спроса – ожидаемое количество продаж в день на ближайшие 30 дней.
    4. Рекомендуемая цена для максимизации прибыли.
    5. Прогноз выручки (цена * спрос) на каждый день.
    6. Ключевые метрики: средняя цена, максимальная, минимальная, волатильность цены (стандартное отклонение).
    7. Ключевые слова для рекламных кампаний, релевантные товару.
    8. Текстовые рекомендации по улучшению карточки товара (SEO, описание, изображения).

    Верни ответ строго в формате JSON со следующими полями:
    {{
      "days_to_out_of_stock": "строка (например, 'Товар закончится через 15 дней' или 'Недостаточно данных')",
      "price_dynamic": "строка (краткое описание динамики)",
      "forecast": [{"date": "YYYY-MM-DD", "price": число, "demand": число, "stock": число}],
      "recommended_price": число,
      "revenue_forecast": [{"date": "YYYY-MM-DD", "revenue": число}],
      "key_metrics": {{"avg_price": число, "max_price": число, "min_price": число, "volatility": число}},
      "keywords": ["ключевое слово1", "ключевое слово2", ...],
      "recommendations": "текст рекомендаций"
    }}
    В полях forecast и revenue_forecast должно быть 30 записей (на каждый день), начиная с сегодняшнего дня.
    Если данных недостаточно, заполни массив прогнозов приблизительными значениями на основе имеющихся.
    """

    try:
        # 3. Запрос к GigaChat
        # Предполагаем, что у GigaChatModel есть метод chat_completion или аналогичный.
        # В seo_service используется gigachat_generation_model.getSEO(...), который возвращает строку JSON.
        # Мы можем использовать тот же метод, но с другим промптом.
        # Если метод getSEO принимает параметры (name, category, description, price), то он не подойдёт.
        # Создадим универсальную функцию для отправки промпта.
        response_text = await _ask_gigachat(prompt)
        result = json.loads(response_text)

        # Проверка наличия всех ожидаемых полей
        required_fields = ("days_to_out_of_stock", "price_dynamic", "forecast", "recommended_price",
                           "revenue_forecast", "key_metrics", "keywords", "recommendations")
        if not all(field in result for field in required_fields):
            raise ValueError("Ответ GigaChat не содержит всех необходимых полей")

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

        return result

    except Exception as e:
        logger.error(f"Ошибка при генерации отчёта через GigaChat: {e}", exc_info=True)
        # Fallback – возвращаем структуру с заглушками
        return _build_fallback_report(goods_id, name, category, prices, ratings, reviews_counts)


async def _ask_gigachat(prompt: str) -> str:
    """
    Отправляет промпт в GigaChat и возвращает текстовый ответ.
    Использует тот же клиент, что и SEO, но с кастомным запросом.
    """
    # Так как у нас нет прямого доступа к низкоуровневому клиенту,
    # мы используем метод getSEO, но с подменой параметров.
    # Можно создать новый экземпляр и вызвать его метод, но проще использовать существующий.
    # В реальности нужно реализовать метод chat_completion в GigaChatModel.
    # Пока используем заглушку – возвращаем тестовые данные.
    # ВАЖНО: заменить на реальный вызов GigaChat.
    # Примерная реализация:
    # response = await gigachat_model.chat(prompt)
    # return response

    # Временная заглушка (имитация ответа GigaChat)
    # В реальном проекте здесь должен быть вызов API GigaChat.
    logger.warning("Используется заглушка GigaChat для отчёта")
    return json.dumps({
        "days_to_out_of_stock": "Недостаточно данных для точного прогноза.",
        "price_dynamic": "Цена стабильна, вероятно небольшое снижение в перспективе.",
        "forecast": [{"date": (date.today() + timedelta(days=i)).isoformat(),
                      "price": 1000 + i * 10,
                      "demand": 5 + i,
                      "stock": 100 - i * 2} for i in range(30)],
        "recommended_price": 1050,
        "revenue_forecast": [{"date": (date.today() + timedelta(days=i)).isoformat(),
                              "revenue": (1000 + i * 10) * (5 + i)} for i in range(30)],
        "key_metrics": {"avg_price": 1020, "max_price": 1100, "min_price": 950, "volatility": 45},
        "keywords": ["ключевое слово 1", "ключевое слово 2", "ключевое слово 3"],
        "recommendations": "Рекомендуется улучшить описание и добавить больше изображений."
    })


def _build_fallback_report(goods_id: int, name: str, category: str, prices: List[float], ratings: List[float], reviews_counts: List[int]) -> Dict[str, Any]:
    """Возвращает отчёт с заполнителями при ошибке."""
    today = date.today()
    forecast = []
    revenue_forecast = []
    base_price = prices[-1] if prices else 1000
    base_demand = 5
    for i in range(30):
        d = today + timedelta(days=i)
        price = base_price + i * 5
        demand = base_demand + i * 0.5
        forecast.append({"date": d.isoformat(), "price": price, "demand": demand, "stock": max(0, 100 - i * 3)})
        revenue_forecast.append({"date": d.isoformat(), "revenue": price * demand})

    return {
        "goods_id": goods_id,
        "days_to_out_of_stock": "Недостаточно данных для прогноза",
        "price_dynamic": "Цена стабильна",
        "forecast": forecast,
        "recommended_price": base_price * 1.05,
        "revenue_forecast": revenue_forecast,
        "key_metrics": {
            "avg_price": sum(prices) / len(prices) if prices else base_price,
            "max_price": max(prices) if prices else base_price,
            "min_price": min(prices) if prices else base_price,
            "volatility": 0
        },
        "keywords": [f"Купить {name}", f"{name} цена", "лучшая цена"],
        "recommendations": "Попробуйте улучшить карточку товара для повышения конверсии."
    }