# Используем правильный образ Playwright + Python
FROM mcr.microsoft.com/playwright/python:v1.62.0-noble

WORKDIR /app

# Копируем requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код проекта
COPY backend /app/backend
COPY db /app/db
COPY config.py /app/config.py

# Открываем порт 80 (как ожидает Amvera по умолчанию)
EXPOSE 80

# Запускаем приложение
CMD ["python", "app.py"]