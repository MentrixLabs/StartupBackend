# Базовый образ Python 3.11
FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей для Playwright
RUN apt-get update && apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libgbm1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libasound2 \
    libatspi2.0-0 \
    libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements.txt из корня проекта (если путь другой, измените)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем браузеры Playwright (с зависимостями)
RUN playwright install --with-deps chromium

# Копируем весь код проекта
COPY . .

# Открываем порт (соответствует containerPort: 8000)
EXPOSE 8000

# Запускаем скрипт app.py
CMD ["python", "app.py"]