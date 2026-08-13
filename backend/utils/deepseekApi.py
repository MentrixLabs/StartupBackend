from openai import OpenAI


class DeepSeekModel:
    def __init__(self, api_key = "sk-683205028d7b4ec19f8fece279cf6b34", base_url = "https://api.deepseek.com", model = "deepseek-chat", project = None, max_tokens = 1500):
        self.client = OpenAI(api_key=api_key, base_url=base_url) if project else OpenAI(api_key=api_key, base_url=base_url, project = project)
        self.model = model
        self.max_tokens = max_tokens


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
        
            Ответ дай в формате JSON:
            {{
                "title": "...",
                "description": "...",
                "keywords": ["слово1", "слово2", ...]
                "advertising_spend_ratio": [old, new]
                "leads": [old, new]
                "CTR": [old, new]
            }}
            """

        response = self.client.chat.completions.create(
            model=self.model,
            response_format = {"type": "text"},
            messages=[
                {"role": "system", "content": "You are a professional SEO manager, you write the most selling texts with the most relevant keywords to the product. Answer in Russian."},
                {"role": "user", "content": prompt},
            ],
            stream=False,
            temperature=0.7,
            max_tokens=self.max_tokens
        )

        return response.choices[0].message.content

    def getConsultation(self, message) -> str:

        response = self.client.chat.completions.create(
            max_completion_tokens = 500,
            model=self.model,
            response_format = {"type": "text"},
            messages=[
                {"role": "system", "content": "You are the best consultant, you always provide research in your answers and indicate their sources. You do not write the general information that I gave you, you only write recommendations and sources. Provide advice on product data. Answer in Russian."},
                {"role": "user", "content": message},
            ],
            stream=False,
            temperature=0.7,
            max_tokens = self.max_tokens
        )

        return response.choices[0].message.content


    def getIG(self, product) -> str:

        response = self.client.chat.completions.create(
            max_completion_tokens = 20,
            max_tokens = 20,
            model=self.model,
            response_format = {"type": "text"},
            messages=[
                {"role": "system", "content": "You are the best marketer, making the most selling text. You were given a picture of a product that will be listed later, so that you could make an infographic. Write a THESIS 4 MOST IMPORTANT SELLING CHARACTERISTICS of this item. Answer in Russian."},
                {"role": "user", "content": product},
            ],
            stream=False,
            temperature=0.7,
            max_output_tokens=self.max_tokens
        )

        return response.choices[0].message.content
