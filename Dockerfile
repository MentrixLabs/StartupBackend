# Используем официальный образ Playwright с Python
FROM mcr.microsoft.com/playwright:python-1.50.0

WORKDIR /app

# Копируем requirements.txt из корня проекта (если путь другой, измените)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Копируем код проекта
COPY backend /app/backend
COPY db /app/db
COPY config.py /app/config.py

# Открываем порт
EXPOSE 8000

# Копируем весь код проекта
COPY . .

# Открываем порт (соответствует containerPort: 8000)
EXPOSE 80

# Запускаем скрипт app.py
CMD ["python", "app.py"]