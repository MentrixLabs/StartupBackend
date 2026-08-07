FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements
COPY utils/requirements/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY backend /app/backend
COPY db /app/db
COPY config.py /app/config.py

# Запуск сервера
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]