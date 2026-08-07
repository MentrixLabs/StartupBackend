from statistics import mean
from datetime import date, timedelta
from typing import List, Dict, Any
from fastapi import HTTPException
from db.db import async_session_maker
from db.ozon.dao import OzonItemDAO
import asyncio


# ВРЕМЕННАЯ ЗАГЛУШКА ДЛЯ ML-МОДЕЛИ
# Замените на реальную функцию из ml.prediction.model
def prediction_days():
    """
    Возвращает фиктивные данные для тестирования отчётов.
    В реальном проекте здесь должна быть ваша ML-модель.
    """
    return {
        "category": "electronics.smartphone",
        "dates": [
            "2019-10-21", "2019-10-23", "2019-10-24", "2019-10-25", "2019-10-26",
            "2019-10-27", "2019-10-29", "2019-10-30", "2019-11-05", "2019-11-06",
            "2019-11-10", "2019-11-11", "2019-11-16", "2019-11-18", "2019-11-19",
            "2019-11-19", "2019-11-20", "2019-11-26", "2019-11-27", "2019-12-04",
            "2019-12-05", "2019-12-06", "2019-12-21", "2019-12-21", "2019-12-22",
            "2019-12-23", "2020-01-16", "2020-01-20", "2020-01-21", "2020-01-22",
            "2020-01-23", "2020-01-24", "2020-01-25", "2020-01-25", "2020-01-26",
            "2020-01-28", "2020-01-29"
        ],
        "prices": [
            333.49, 333.49, 333.49, 333.49, 333.49,
            333.49, 301.14, 301.14, 300.91, 300.91,
            300.91, 300.91, 300.91, 300.91, 300.91,
            359.47, 359.47, 300.91, 300.91, 300.91,
            300.91, 300.91, 300.91, 231.64, 231.64,
            231.64, 213.62, 213.62, 213.62, 213.62,
            213.62, 213.62, 213.62, 244.51, 244.51,
            213.62, 213.62
        ],
        "counts": [
            2, 1, 1, 1, 1,
            1, 4, 1, 1, 1,
            5, 2, 2, 1, 2,
            1, 1, 3, 1, 2,
            3, 2, 1, 4, 2,
            2, 3, 2, 1, 3,
            5, 5, 1, 5, 5,
            4, 2
        ]
    }


async def generate_report_data(goods_id: int, user_id: int) -> Dict[str, Any]:
    """
    Генерирует данные отчёта по прогнозу остатков для указанного товара.
    Возвращает словарь с текстовыми полями и массивом прогнозов по дням.
    """
    # 1. Проверяем, что товар существует и принадлежит пользователю
    async with async_session_maker() as session:
        goods = await OzonItemDAO.find_one_or_none(id=goods_id, user_id=user_id)
        if not goods:
            raise HTTPException(status_code=404, detail="Товар не найден или доступ запрещён")

    # 2. Запускаем ML-модель (заглушка)
    try:
        # Запускаем синхронную функцию в отдельном потоке, чтобы не блокировать event loop
        predicted_data = await asyncio.to_thread(prediction_days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка ML-модели: {str(e)}")

    if not predicted_data:
        raise HTTPException(status_code=404, detail="Прогноз не удалось построить")

    # 3. Формируем структурированный ответ
    report = await _build_report_json(predicted_data)
    report["goods_id"] = goods_id
    return report


async def _build_report_json(predicted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Формирует JSON-структуру из прогноза.
    Ожидает словарь с ключами dates, prices, counts.
    """
    dates = predicted_data.get("dates", [])
    prices = predicted_data.get("prices", [])
    counts = predicted_data.get("counts", [])

    daysCount = len(prices)
    if daysCount == 0:
        return {
            "days_to_out_of_stock": "Недостаточно данных для прогноза.",
            "price_dynamic": "Нет данных о ценах.",
            "forecast": [],
            "raw_data": predicted_data
        }

    # Генерируем даты, начиная с сегодняшнего дня
    date_pipeline = [date.today() + timedelta(days=i) for i in range(daysCount)]
    count_pipeline = counts  # предполагаем, что это общий остаток (FBS+FBO)

    # Определяем день, когда товар закончится
    days_to_out_of_stock = f"Товар ещё не закончится {daysCount} дней."
    for i, count in enumerate(count_pipeline):
        if count == 0:
            days_to_out_of_stock = f"Товар закончится через {i} дней"
            break

    avg_price = mean(prices) if prices else 0
    price_dynamic = f"Цена соответствующая ожиданиям рынка из соображений out of stock: {avg_price:.2f}"

    # Строим массив прогнозов по дням
    forecast = []
    for i in range(daysCount):
        forecast.append({
            "date": date_pipeline[i].isoformat(),
            "remaining": count_pipeline[i] if i < len(count_pipeline) else 0,
            "price": prices[i] if i < len(prices) else 0,
        })

    return {
        "days_to_out_of_stock": days_to_out_of_stock,
        "price_dynamic": price_dynamic,
        "forecast": forecast,
        "raw_data": predicted_data,  # опционально, для отладки
    }