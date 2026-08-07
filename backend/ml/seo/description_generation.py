from transformers import GPT2LMHeadModel, GPT2Tokenizer

model_name = "sberbank-ai/rugpt3small_based_on_gpt2"
tokenizer = GPT2Tokenizer.from_pretrained(model_name)
model = GPT2LMHeadModel.from_pretrained(model_name)

def description_generation(question):
    prompt = f"Название товара: {question}\Описание и характеристики к товару:"

    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(
        **inputs,
        max_length=200,  # Увеличиваем длину для развёрнутого ответа
        num_beams=5,     # Улучшает качество (но медленнее)
        no_repeat_ngram_size=3,  # Избегаем повторов
        early_stopping=True
    )

    answer = tokenizer.decode(outputs[0], skip_special_tokens=True)

    answer = answer.replace(f"Название товара: {question}\Описание и характеристики к товару:", '')
    
    return answer
