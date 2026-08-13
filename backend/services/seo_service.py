import json
from datetime import datetime
from typing import Dict, Any
from fastapi import HTTPException
from sqlalchemy import select, desc
from openai import AsyncOpenAI
from backend.utils.deepseekApi import DeepSeekModel
from db.db import async_session_maker
from db.ozon.dao import OzonItemDAO, OzonItemCategoryDAO, OzonItemHistoryDAO, SeoDataDAO
from config import settings

generation_model = DeepSeekModel(
    api_key=settings.YANDEX_CLOUD_API_KEY,
    base_url=settings.BASE_AI_URL,
    model=f"gpt://{settings.YANDEX_CLOUD_FOLDER}/{settings.YANDEX_CLOUD_MODEL}",
    project=settings.YANDEX_CLOUD_FOLDER,
    max_tokens=1500
)

async def generate_seo_for_goods(goods_id: int, user_id: int) -> Dict[str, Any]:
    # 1. Получаем данные товара
    async with async_session_maker() as session:
        goods = await OzonItemDAO.find_one_or_none(id=goods_id, user_id=user_id)
        if not goods:
            raise HTTPException(status_code=404, detail="Товар не найден или доступ запрещён")

        name = goods.cardname or "Товар"
        description = goods.description or ""

        categories = await OzonItemCategoryDAO.find_all(item_id=goods.id)
        category = categories[0].category if categories else ""

        history = await OzonItemHistoryDAO.find_all(item_id=goods.id)
        price = None
        if history:
            sorted_history = sorted(history, key=lambda h: h.record_date, reverse=True)
            price = sorted_history[0].price

    # 2. Генерируем SEO
    try:
        content = generation_model.getSEObyYandex(name, category, description, price)
        result = json.loads(content)

        required = ("title", "description", "keywords", "advertising_spend_ratio", "leads", "CTR")
        if not all(k in result for k in required):
            raise ValueError("Ответ не содержит необходимых полей")

        # 3. Сохраняем в БД
        async with async_session_maker() as session:
            existing = await SeoDataDAO.find_one_or_none(goods_id=goods_id)
            data = {
                "generated_title": result["title"],
                "generated_description": result["description"],
                "generated_keywords": result["keywords"],
                "summary": result.get("summary", ""),
                "advertising_spend_ratio": result["advertising_spend_ratio"],
                "leads": result["leads"],
                "ctr": result["CTR"],
            }
            if existing:
                # обновляем
                await SeoDataDAO.update(goods_id=goods_id, **data)
            else:
                await SeoDataDAO.add(goods_id=goods_id, **data)

        # 4. Возвращаем
        return {
            "title": result["title"],
            "description": result["description"],
            "keywords": result["keywords"],
            "advertising_spend_ratio": result["advertising_spend_ratio"],
            "leads": result["leads"],
            "CTR": result["CTR"],
        }
    except Exception as e:
        print(f"Ошибка генерации SEO: {e}")
        # fallback
        return {
            "title": name[:60],
            "description": f"Отличный выбор – {name}"[:300],
            "keywords": [f"Купить {name}", f"{name} цена", "лучшая цена", f"{category} {name}"] if category else [f"Купить {name}", f"{name} цена", "лучшая цена"],
            "advertising_spend_ratio": [0, 0],
            "leads": [0, 0],
            "CTR": [0, 0],
        }