from statistics import mean
from datetime import date, timedelta
from typing import List, Dict, Any
from fastapi import HTTPException
from db.db import async_session_maker
from db.ozon.dao import OzonDAO
import asyncio
#from backend.ml.remainder_prediction.model import prediction_days  # путь к вашей ML-модели


def prediction_days():
    return {"category": "electronics.smartphone", "dates": ["2019-10-21", "2019-10-23", "2019-10-24", "2019-10-25", "2019-10-26", "2019-10-27", "2019-10-29", "2019-10-30", "2019-11-05", "2019-11-06", "2019-11-10", "2019-11-11", "2019-11-16", "2019-11-18", "2019-11-19", "2019-11-19", "2019-11-20", "2019-11-26", "2019-11-27", "2019-12-04", "2019-12-05", "2019-12-06", "2019-12-21", "2019-12-21", "2019-12-22", "2019-12-23", "2020-01-16", "2020-01-20", "2020-01-21", "2020-01-22", "2020-01-23", "2020-01-24", "2020-01-25", "2020-01-25", "2020-01-26", "2020-01-28", "2020-01-29"], "prices": [333.49, 333.49, 333.49, 333.49, 333.49, 333.49, 301.14, 301.14, 300.91, 300.91, 300.91, 300.91, 300.91, 300.91, 300.91, 359.47, 359.47, 300.91, 300.91, 300.91, 300.91, 300.91, 300.91, 231.64, 231.64, 231.64, 213.62, 213.62, 213.62, 213.62, 213.62, 213.62, 213.62, 244.51, 244.51, 213.62, 213.62], "counts": [2, 1, 1, 1, 1, 1, 4, 1, 1, 1, 5, 2, 2, 1, 2, 1, 1, 3, 1, 2, 3, 2, 1, 4, 2, 2, 3, 2, 1, 3, 5, 5, 1, 5, 5, 4, 2]}
async def generate_report_data(goods_id: int, user_id: int) -> Dict[str, Any]:
    """
    Генерирует данные отчёта по прогнозу остатков для указанного товара.
    Возвращает словарь с текстовыми полями и массивом прогнозов по дням.
    """
    async with async_session_maker() as session:
        goods = await OzonDAO.find_one_or_none(id=goods_id, user_id=user_id)
        if not goods:
            raise HTTPException(status_code=404, detail="Товар не найден или доступ запрещён")

    # Запускаем ML-модель (синхронную) в отдельном потоке, чтобы не блокировать событийный цикл
    try:
        predicted_data = await asyncio.to_thread(prediction_days, goods_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка ML-модели: {str(e)}")

    if not predicted_data:
        raise HTTPException(status_code=404, detail="Прогноз не удалось построить")

    # Формируем структурированный ответ
    report = await _build_report_json(predicted_data)
    report["goods_id"] = goods_id
    return report


async def _build_report_json(predicted_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Формирует JSON-структуру из прогноза"""
    data_pipeline = predicted_data[0]
    daysCount = len(data_pipeline["price"])
    date_pipeline = [date.today() + timedelta(days=i) for i in range(daysCount)]
    count_from_pipeline = [
        data_pipeline["count_from_FBS"][i] + data_pipeline["count_from_FBO"][i]
        for i in range(daysCount)
    ]
    price_pipeline = data_pipeline["price"]

    # Определяем день, когда товар закончится
    days_to_out_of_stock = f"Товар ещё не закончится {daysCount} дней."
    for i, count in enumerate(count_from_pipeline):
        if count == 0:
            days_to_out_of_stock = f"Товар закончится через {i} дней"
            break

    avg_price = mean(price_pipeline) if price_pipeline else 0
    price_dynamic = f"Цена соответствующая ожиданиям рынка из соображений out of stock: {avg_price:.2f}"

    # Строим массив прогнозов по дням
    forecast = []
    for i in range(daysCount):
        forecast.append({
            "date": date_pipeline[i].isoformat(),
            "remaining": count_from_pipeline[i],
            "price": price_pipeline[i],
            # Если есть дополнительные данные, можно добавить
        })

    return {
        "days_to_out_of_stock": days_to_out_of_stock,
        "price_dynamic": price_dynamic,
        "forecast": forecast,
        "raw_data": data_pipeline,  # опционально, если нужно для отладки
    }