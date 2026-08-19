import json
from datetime import datetime
from typing import Dict, Any
from fastapi import HTTPException
from sqlalchemy import select, desc
from openai import AsyncOpenAI
from backend.utils.deepseekApi import DeepSeekModel
from backend.utils.GigaChatAPI import GigaChatModel
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
gigachat_generation_model = GigaChatModel(credentials = settings.SBER_AUTHORIZATION_KEY,
                                          scope = "GIGACHAT_API_PERS")

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
        content = gigachat_generation_model.getSEO(name, category, description, price)
        #content = generation_model.getSEObyYandex(name, category, description, price)
        result = json.loads(content)

        required = ("title", "description", "keywords", "summary", "advertising_spend_ratio", "leads", "CTR")
        if not all(k in result for k in required):
            raise ValueError("Ответ не содержит необходимых полей")
        
        summary_value = result.get("summary")
        if isinstance(summary_value, list):
            summary_value = " ".join(summary_value)  # или "\n".join(summary_value)
        elif summary_value is None:
            summary_value = ""

        seo_data = {
            "generated_title": result["title"],
            "generated_description": result["description"],
            "generated_keywords": result["keywords"],
            "summary": summary_value,
            "advertising_spend_ratio": [float(x) for x in result["advertising_spend_ratio"]],
            "leads": [float(x) for x in result["leads"]],
            "ctr": [float(x) for x in result["CTR"]],
        }

        # 3. Сохраняем в БД
        async with async_session_maker() as session:
            existing = await SeoDataDAO.find_one_or_none(goods_id=goods_id)
            if existing:
                await SeoDataDAO.update(goods_id=goods_id, **seo_data)
            else:
                await SeoDataDAO.add(goods_id=goods_id, **seo_data)

        # 4. Возвращаем
        return {
            "title": result["title"],
            "description": result["description"],
            "keywords": result["keywords"],
            "advertising_spend_ratio": result["advertising_spend_ratio"],
            "leads": result["leads"],
            "CTR": result["CTR"],
        }
    except Exception as e:# Fallback – тоже сохраняем в БД, чтобы у пользователя была запись
        print(f"Ошибка генерации SEO для goods_id={goods_id}: {e}", exc_info=True)
        fallback = {
            "title": name[:60],
            "description": f"Отличный выбор – {name}"[:300],
            "keywords": [f"Купить {name}", f"{name} цена", "лучшая цена", f"{category} {name}"] if category else [f"Купить {name}", f"{name} цена", "лучшая цена"],
            "advertising_spend_ratio": [0.0, 0.0],
            "leads": [0.0, 0.0],
            "ctr": [0.0, 0.0],
        }
        seo_data = {
            "generated_title": fallback["title"],
            "generated_description": fallback["description"],
            "generated_keywords": fallback["keywords"],
            "summary": summary_value,
            "advertising_spend_ratio": fallback["advertising_spend_ratio"],
            "leads": fallback["leads"],
            "ctr": fallback["ctr"],
        }
        # Сохраняем fallback в БД
        async with async_session_maker() as session:
            existing = await SeoDataDAO.find_one_or_none(goods_id=goods_id)
            if existing:
                await SeoDataDAO.update(goods_id=goods_id, **seo_data)
            else:
                await SeoDataDAO.add(goods_id=goods_id, **seo_data)
        return fallback