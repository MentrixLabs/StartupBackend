import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import HTTPException
from sqlalchemy import select, desc
from openai import AsyncOpenAI

from backend.utils.deepseekApi import DeepSeekModel

from db.db import async_session_maker
from db.ozon.dao import OzonItemDAO, OzonItemCategoryDAO, OzonItemHistoryDAO
from config import settings

generation_model = DeepSeekModel(api_key = settings.YANDEX_CLOUD_API_KEY,
                                 base_url = settings.BASE_AI_URL,
                                 model = settings.YANDEX_CLOUD_FOLDER/settings.YANDEX_CLOUD_MODEL,
                                 project = settings.YANDEX_CLOUD_FOLDER,
                                 max_tokens = 1500)    

async def generate_seo_for_goods(goods_id: int, user_id: int) -> Dict[str, Any]:
    """
    Генерирует SEO-оптимизацию для товара через DeepSeek API.
    Возвращает словарь с полями: title, description, keywords.
    """
    # 1. Получаем данные товара
    async with async_session_maker() as session:
        goods = await OzonItemDAO.find_one_or_none(id=goods_id, user_id=user_id)
        if not goods:
            raise HTTPException(status_code=404, detail="Товар не найден или доступ запрещён")

        name = goods.cardname or "Товар"
        description = goods.description or ""

        # 2. Получаем категории (берём первую, если есть)
        categories = await OzonItemCategoryDAO.find_all(item_id=goods.id)
        category = categories[0].category if categories else ""

        # 3. Получаем последнюю цену из истории
        history = await OzonItemHistoryDAO.find_all(item_id=goods.id)
        price = None
        if history:
            # Сортируем по дате, берём последнюю
            sorted_history = sorted(history, key=lambda h: h.record_date, reverse=True)
            price = sorted_history[0].price

    try:
        generation_model = DeepSeekModel(api_key = settings.YANDEX_CLOUD_API_KEY,
                                 base_url = settings.BASE_AI_URL,
                                 model = settings.YANDEX_CLOUD_FOLDER/settings.YANDEX_CLOUD_MODEL,
                                 project = settings.YANDEX_CLOUD_FOLDER,
                                 max_tokens = 1500)  
        content = generation_model.getSEO(name, category, description, price)
        result = json.loads(content)

        if not all(k in result for k in ("title", "description", "keywords")):
            raise ValueError("Ответ не содержит необходимых полей")
        
        return {
            "title": result["title"][:60],
            "description": result["description"][:300],
            "keywords": result["keywords"][:10]
        }
    except Exception as e:
        print(f"Ошибка: {e}")
        
        return {
            "title": name[:60],
            "description": f"Отличный выбор – {name}"[:300],
            "keywords": [f"Купить {name}", f"{name} цена", "лучшая цена", f"{category} {name}"] if category else [f"Купить {name}", f"{name} цена", "лучшая цена"]
        }