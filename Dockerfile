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

RUN pip install --no-cache-dir -r requirements.txt
# Устанавливаем браузеры Playwright
RUN playwright install --with-deps chromium

# Копируем код
COPY backend /app/backend
COPY db /app/db
COPY config.py /app/config.py

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]