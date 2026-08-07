from openai import OpenAI


client = OpenAI(api_key="sk-683205028d7b4ec19f8fece279cf6b34", base_url="https://api.deepseek.com")

def getResponse(product_name) -> str:

    response = client.chat.completions.create(
        model="deepseek-chat",
        response_format = {"type": "text"},
        messages=[
            {"role": "system", "content": "You are a professional SEO manager, you write the most selling texts with the most relevant keywords to the product. Answer in Russian."},
            {"role": "user", "content": product_name},
        ],
        stream=False,
        temperature=0.7,
    )

    return response.choices[0].message.content


def getConsultation(message) -> str:

    response = client.chat.completions.create(
        max_completion_tokens = 500,
        max_tokens = 500,
        model="deepseek-chat",
        response_format = {"type": "text"},
        messages=[
            {"role": "system", "content": "You are the best consultant, you always provide research in your answers and indicate their sources. You do not write the general information that I gave you, you only write recommendations and sources. Provide advice on product data. Answer in Russian."},
            {"role": "user", "content": message},
        ],
        stream=False,
        temperature=0.7,
    )

    return response.choices[0].message.content


def getIG(product) -> str:

    response = client.chat.completions.create(
        max_completion_tokens = 20,
        max_tokens = 20,
        model="deepseek-chat",
        response_format = {"type": "text"},
        messages=[
            {"role": "system", "content": "You are the best marketer, making the most selling text. You were given a picture of a product that will be listed later, so that you could make an infographic. Write a THESIS 4 MOST IMPORTANT SELLING CHARACTERISTICS of this item. Answer in Russian."},
            {"role": "user", "content": product},
        ],
        stream=False,
        temperature=0.7,
    )

    return response.choices[0].message.content
