import os
from openai import AsyncOpenAI
from typing import Dict, Any, List, Optional
from fastapi import HTTPException
from db.db import async_session_maker
from db.ozon.dao import OzonDAO
from config import settings

# Инициализация клиента DeepSeek (или OpenAI)
# DeepSeek использует тот же SDK, но с другим base_url
DS_API_Key = settings.DEEPSEEK_API_KEY

client = AsyncOpenAI(
    api_key=settings.DEEPSEEK_API_KEY,  # добавьте переменную в .env
    base_url="https://api.deepseek.com/v1",  # или "https://api.deepseek.com"
) if DS_API_Key else None

async def generate_seo_for_goods(goods_id: int, user_id: int) -> Dict[str, Any]:
    """
    Генерирует SEO-оптимизацию для товара через DeepSeek API.
    Возвращает словарь с полями: title, description, keywords.
    """
    # 1. Получаем данные товара из БД
    async with async_session_maker() as session:
        goods = await OzonDAO.find_one_or_none(id=goods_id, user_id=user_id)
        if not goods:
            raise HTTPException(status_code=404, detail="Товар не найден или доступ запрещён")

        # Извлекаем информацию о товаре (адаптируйте под вашу структуру)
        # Предположим, что у нас есть поля: cardname, description, category, price и т.д.
        name = goods.cardname or "Товар"
        description = goods.description or ""
        category = goods.categories[0] if goods.categories and len(goods.categories) > 0 else ""
        price = goods.prices[0][0] if goods.prices and goods.prices[0] else None

    # 2. Формируем промпт для DeepSeek
    prompt = f"""
    Ты — профессиональный копирайтер для маркетплейсов. Напиши SEO-оптимизированный контент для товара.

    Название: {name}
    Категория: {category}
    Описание: {description}
    Цена: {price} руб.

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

    # 3. Отправляем запрос к DeepSeek
    try:
        response = await client.chat.completions.create(
            model="deepseek-chat",  # или "deepseek-coder" – используйте подходящую модель
            messages=[
                {"role": "system", "content": "Ты — помощник, генерирующий SEO-контент. Отвечай строго в формате JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500,
            response_format={"type": "json_object"}  # если поддерживается
        )
        # Извлекаем JSON из ответа
        content = response.choices[0].message.content
        import json
        result = json.loads(content)
        # Валидация полей
        if not all(k in result for k in ("title", "description", "keywords")):
            raise ValueError("Ответ не содержит необходимых полей")
        return {
            "title": result["title"][:60],
            "description": result["description"][:300],
            "keywords": result["keywords"][:10]
        }
    except:
        return {
                    "title": name,
                    "description": f"Очень крутой {name}",
                    "keywords": [f"Ключевые слова для {name}"]
                }