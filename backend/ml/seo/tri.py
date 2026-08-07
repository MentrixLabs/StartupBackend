import re
import subprocess
import ollama

MODEL_NAME = 'mistral:7b-instruct-v0.2-q4_K_M'

subprocess.Popen(["ollama", "serve"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

prompt1 = f'''
Вы дизайнер-маркетолог, напишите на русском языке короткие ключевые свойства товара для картинки товара по его описанию.
Шаблон свойств:
слой:
текст: [свойство]
текст: [свойство]
текст: [свойство]
слой:
текст: [свойство]
текст: [свойство]
текст: [свойство]
Не пишите пояснения и лишние символы.
Характеристики товара:
'''

def generate_with_prompt(prompt, input_text):
    response = ollama.chat(
        model=MODEL_NAME,
        messages=[
            {
                'role': 'user',
                'content': f'{prompt} {input_text}',
            },
        ]
    )
    return response['message']['content']

def product_properties(description):
    step_result = generate_with_prompt(prompt1, description)
    return step_result

def parse_properties(text):
    pattern = r'слой:\s*(.*?)(?=\s*слой:|\s*$)'
    layers_matches = re.finditer(pattern, text, re.DOTALL)
    
    result = []
    for layer_match in layers_matches:
        layer_text = layer_match.group(1).strip()
        # Извлекаем все свойства из текста слоя
        properties = re.findall(r'текст:\s*(.*?)\s*(?=\s*текст:|\s*$)', layer_text)
        if properties:
            result.append([prop.strip() for prop in properties if prop.strip()])
    
    return result

'''
Скачай Ollama https://ollama.com/download (Windows/Linux/Mac)
Включить ollama serve
Скачай модель ollama pull mistral:7b-instruct-v0.2-q4_K_M
'''

if __name__ == '__main__':
    description = input("Введите описание товара: ")
    result = product_properties(description)
    print("\nКлючевые свойства товара:")
    print(result)
    print(parse_properties(result))
