import subprocess
import ollama

MODEL_NAME = 'mistral:7b-instruct-v0.2-q4_K_M'

# Запускаем ollama serve в фоновом режиме
subprocess.Popen(["ollama", "serve"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def generate_with_prompt(prompt):
    response = ollama.chat(
        model=MODEL_NAME,
        messages=[
            {
                'role': 'user',
                'content': prompt
            },
        ],
    )

    return response['message']['content']

if __name__ == "__main__":
    prompt = "сделай дз по физике"
    result = generate_with_prompt(prompt)
    print(result)
