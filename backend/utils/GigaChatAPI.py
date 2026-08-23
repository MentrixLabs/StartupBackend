from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole
import re

from config import settings



class GigaChatModel:
    def __init__(self, credentials = settings.SBER_AUTHORIZATION_KEY, scope="GIGACHAT_API_PERS", timeout = 200):
        self.client = GigaChat(
            base_url="https://api.giga.chat/v1",
            credentials=credentials,
            scope=scope,
            verify_ssl_certs=False,
            timeout = timeout
        )

    def getSEO(self, product_name, category, description, price) -> str:
        prompt = f"""
            Ты — профессиональный копирайтер для маркетплейсов. Напиши SEO-оптимизированный контент для товара.
        
            Название товара: {product_name}
            Категория товара: {category}
            Описание товара: {description}
            Цена товара: {price if price else "не указана"} руб.
        
            Улучши текущее SEO:
            1. Заголовок (привлекательный, с ключевыми словами).
            2. Описание (продающее, с LSI-фразами).
            3. Ключевые слова (список из 5–10 слов и фраз, релевантных для поиска).
            4. Спрогнозируй, на сколько понизится доля рекламных расходов, поднимится CTR и количество лидов с новыми SEO и ключевыми словами
        
            Ответ дай ИСКЛЮЧИТЕЛЬНО в формате JSON БЕЗ ВСЕГО ОСТАЛЬНОГО, ЧТО В ЭТОТ JSON НЕ ВХОДИТ:
            {{
                "title": "...",
                "description": "...",
                "keywords": ["слово1", "слово2", ...],
                "summary": [...],
                "advertising_spend_ratio": [float(old), float(new)],
                "leads": [float(old), float(new)],
                "CTR": [float(old), float(new)]
            }}
            """
               
        chat = Chat(
            model="GigaChat-3-Ultra",
            messages=[Messages(role=MessagesRole.USER, content=prompt)],
        )

        response = self.client.chat(chat)
        content = response.choices[0].message.content

        json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
        if not json_match:
            # 2. Если нет Markdown, ищем первое полное JSON-объект
            json_match = re.search(r'(\{.*\})', content, re.DOTALL)

        if json_match:
            return json_match.group(1)  # возвращаем только JSON-строку
        else:
            # Если ничего не найдено, возвращаем как есть (можно выбросить ошибку)
            raise ValueError("Не удалось извлечь JSON из ответа модели")

    def getResponseByPromt(self, prompt) -> str:

        chat = Chat(
            model="GigaChat-3-Ultra",
            messages=[Messages(role=MessagesRole.USER, content=prompt)],
        )
    
        response = self.client.chat(chat)
        content = response.choices[0].message.content
    
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
        if not json_match:
            # 2. Если нет Markdown, ищем первое полное JSON-объект
            json_match = re.search(r'(\{.*\})', content, re.DOTALL)
    
        if json_match:
            return json_match.group(1)  # возвращаем только JSON-строку
        else:
            # Если ничего не найдено, возвращаем как есть (можно выбросить ошибку)
            raise ValueError("Не удалось извлечь JSON из ответа модели")


if __name__ == '__main__':
    import json
    model = GigaChatModel()
    seo = model.getSEO("product_name", "category: Any", "description: Any", "price: Any")
    try:
        result = json.loads(seo)
        print(result)
    except json.JSONDecodeError as e:
        print(f"Ошибка парсинга JSON: {e}")
        print("Ответ модели:", seo)