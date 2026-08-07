import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import HTTPException
from sqlalchemy import select, desc
from openai import AsyncOpenAI

from db.db import async_session_maker
from db.ozon.dao import OzonItemDAO, OzonItemCategoryDAO, OzonItemHistoryDAO
from config import settings

# Инициализация клиента DeepSeek (если есть ключ)
client = None
if settings.DEEPSEEK_API_KEY:
    client = AsyncOpenAI(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com/v1",
    )

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

    # 4. Формируем промпт для DeepSeek
    prompt = f"""
    Ты — профессиональный копирайтер для маркетплейсов. Напиши SEO-оптимизированный контент для товара.

    Название: {name}
    Категория: {category}
    Описание: {description}
    Цена: {price if price else "не указана"} руб.

    Создай:
    1. Заголовок (до 60 символов, привлекательный, с ключевыми словами).
    2. Описание (до 300 символов, продающее, с LSI-фразами).
    3. Ключевые слова (список из 5–10 слов и фраз, релевантных для поиска).

    Ответ дай в формате JSON:
    {{
        "title": "...",
        "description": "...",
        "keywords": ["слово1", "слово2", ...]
    }}
    """

    # 5. Если клиент не инициализирован или запрос не удался, возвращаем заглушку
    if not client:
        return {
            "title": name[:60],
            "description": f"Очень крутой {name}"[:300],
            "keywords": [f"Купить {name}", f"{name} цена", f"{category} {name}"] if category else [f"Купить {name}", f"{name} цена"]
        }

    try:
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "Ты — помощник, генерирующий SEO-контент. Отвечай строго в формате JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        result = json.loads(content)
        if not all(k in result for k in ("title", "description", "keywords")):
            raise ValueError("Ответ не содержит необходимых полей")
        return {
            "title": result["title"][:60],
            "description": result["description"][:300],
            "keywords": result["keywords"][:10]
        }
    except Exception as e:
        # В случае ошибки возвращаем заглушку (можно также логировать)
        return {
            "title": name[:60],
            "description": f"Отличный выбор – {name}"[:300],
            "keywords": [f"Купить {name}", f"{name} цена", "лучшая цена", f"{category} {name}"] if category else [f"Купить {name}", f"{name} цена", "лучшая цена"]
        }