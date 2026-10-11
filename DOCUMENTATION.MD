## 1. Обзор

Backend предоставляет REST API для управления товарами, генерации SEO-контента, поиска инфографики, создания отчётов, управления тарифами и платежами. Код написан на Python 3.12 с использованием FastAPI, SQLAlchemy (async), Pydantic.

## 2. Установка и запуск

### 2.1. Требования
- Python 3.12+
- PostgreSQL (или другая БД, поддерживаемая asyncpg)
- Установленный пакетный менеджер `pip`

### 2.2. Шаги

```bash
cd StartupBackend
python -m venv venv
source venv/bin/activate  # для Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # заполнить переменные
```

### 2.3. Переменные окружения (`.env`)

| Переменная | Описание |
|------------|----------|
| `DATABASE_URL` | URL подключения к PostgreSQL (asyncpg) |
| `SECRET_KEY` | Секретный ключ для JWT |
| `ALGORITHM` | Алгоритм JWT (по умолчанию HS256) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Время жизни токена |
| `SBER_AUTHORIZATION_KEY` | Ключ авторизации GigaChat |
| `YANDEX_CLOUD_API_KEY` | Ключ Yandex Cloud (для DeepSeek) – опционально |
| `YOOKASSA_SHOP_ID` | ID магазина ЮKassa |
| `YOOKASSA_SECRET_KEY` | Секретный ключ ЮKassa |
| `PAYMENT_MOCK_ENABLED` | Включить заглушку платежей (true/false) |
| `BASE_AI_URL` | URL для AI-моделей |

### 2.4. Запуск

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Приложение также запускается через `app.py`.

## 3. Архитектура

### 3.1. Структура каталогов

```
StartupBackend/
├── app.py                 # Точка входа
├── backend/
│   ├── api/               # Роутеры FastAPI
│   │   ├── auth.py        # Регистрация, логин, /me, /update_tg_id
│   │   ├── goods.py       # CRUD товаров, парсинг, перепарсинг, история остатков
│   │   ├── seo.py         # Генерация SEO, история
│   │   ├── infographics.py # Генерация и улучшение инфографики
│   │   ├── reports.py     # Генерация, получение, удаление, скачивание отчётов
│   │   ├── stats.py       # Статистика (активность, распределение, рекомендации)
│   │   ├── payment.py     # Создание платежа, статус, вебхук
│   │   └── user.py        # Статус пользователя (план, лимиты)
│   ├── core/              # Ядро (security, dependencies)
│   │   ├── security.py    # Хеширование, JWT
│   │   └── dependencies.py # get_current_user
│   ├── services/          # Бизнес-логика
│   │   ├── seo_service.py      # Генерация и сохранение SEO
│   │   ├── report_service.py   # Генерация отчётов, проверка cooldown
│   │   ├── payment_service.py  # Создание платежей, вебхуки
│   │   ├── usage_service.py    # Проверка лимитов, получение использования
│   │   ├── image_enhancement_service.py # Коллаж + текст (PIL)
│   │   └── infographics_service.py # Генерация через Kandinsky (заглушка)
│   ├── schemas/           # Pydantic-схемы
│   ├── utils/             # Утилиты (парсер, GigaChat API)
│   └── config/            # Конфигурация (plans.py, настройки)
├── db/                    # Модели, DAO, сессии
│   ├── db.py              # engine, async_session_maker
│   ├── user/              # Модель User, Profile, DAO
│   ├── ozon/              # Модели OzonItem, SeoData, InfographicsData, Report, PaymentTransaction, DAO
│   └── dao/               # BaseDAO
└── bot/                   # (опционально) код Telegram-бота
```

### 3.2. Основные модули и классы

- **`app.py`** – инициализирует FastAPI, подключает CORS, регистрирует роутеры.
- **`BaseDAO`** – абстрактный класс с методами `find_all`, `find_one_or_none`, `add`, `update`, `delete` (использует `async_session_maker`).
- **Модели SQLAlchemy** описаны в `db/ozon/models.py` и `db/user/models.py`; содержат поля, связи, каскадное удаление.
- **Сервисы** содержат основную бизнес-логику и вызывают DAO.
- **Роутеры** обрабатывают HTTP-запросы, вызывают сервисы и возвращают Pydantic-схемы.

## 4. API Эндпоинты

### 4.1. Аутентификация (`/auth`)

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/auth/register` | Регистрация нового пользователя (username, email, password). Возвращает `UserOut`. |
| `POST` | `/auth/login` | Вход (OAuth2PasswordRequestForm). Возвращает `Token` (access_token). |
| `GET` | `/auth/me` | Получение текущего пользователя (JWT). |
| `PUT` | `/auth/update_tg_id` | Привязка Telegram ID к пользователю. |

### 4.2. Товары (`/goods`)

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/goods` | Список товаров пользователя (с пагинацией). |
| `GET` | `/goods/{id}` | Детали товара. |
| `POST` | `/goods` | Создание товара (передаётся URL, парсится). Проверка лимита `add_goods`. |
| `DELETE` | `/goods/{id}` | Удаление товара (каскадно). |
| `POST` | `/goods/{id}/reparse` | Перепарсинг данных товара. |
| `POST` | `/goods/{id}/stock-history` | Обновление истории остатков (fbs_count). |

### 4.3. SEO (`/seo`)

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/seo/generate` | Генерация SEO для товара. Проверка лимита `generate_seo`. |
| `GET` | `/seo/history/{goods_id}` | Получение последнего SEO и конкурентов. |

### 4.4. Инфографика (`/infographics`)

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/infographics/generate` | Генерация новых изображений (Kandinsky). Проверка `generate_infographics`. |
| `POST` | `/infographics/enhance` | Улучшение существующих изображений (коллаж+текст). Проверка `enhance_infographics`. |
| `GET` | `/infographics/{goods_id}` | Получение сохранённых изображений (generated и enhanced). |

### 4.5. Отчёты (`/reports`)

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/reports` | Список отчётов пользователя (пагинация). |
| `GET` | `/reports/{id}` | Информация об отчёте. |
| `POST` | `/reports/generate` | Создание нового отчёта (проверка cooldown). |
| `DELETE` | `/reports/{id}` | Удаление отчёта. |
| `GET` | `/reports/{id}/download/pdf` | Скачивание PDF (доступно по тарифу). |
| `GET` | `/reports/{id}/download/excel` | Скачивание Excel (только Бизнес). |

### 4.6. Статистика (`/stats`)

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/stats/weekly-activity` | Активность за неделю (SEO/инфографика по дням). |
| `GET` | `/stats/content-distribution` | Распределение контента (SEO, инфографика, отчёты). |
| `GET` | `/stats/recommendation` | Планка на неделю (цели по SEO и инфографике). |

### 4.7. Платежи (`/payment`)

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/payment/create` | Создание платежа (сумма, описание). Возвращает ссылку на оплату. |
| `GET` | `/payment/status/{order_id}` | Получение статуса транзакции. |
| `POST` | `/payment/webhook` | Вебхук от ЮKassa (обновление статуса). |

### 4.8. Пользователь (`/user`)

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/user/status` | Статус пользователя: план, лимиты, использование (товары, SEO сегодня, инфографика сегодня). |

## 5. Модели данных (основные)

### 5.1. `User`
- `id`, `username`, `email`, `hashed_password`, `tg_id`, `plan` (free/starter/business), `created_at`.

### 5.2. `OzonItem`
- `id`, `user_id`, `cardname`, `description`, `url`, `product_id`, `provider`, `brand`, `original_price`, `currency`, `rating`, `reviews_count`, `main_imgs`, `desc_imgs`, `created_at`, связи с категориями, историей, отзывами, SEO, инфографикой, отчётами.

### 5.3. `SeoData`
- `goods_id`, `generated_title`, `generated_description`, `generated_keywords`, `summary`, `advertising_spend_ratio`, `leads`, `ctr`, `created_at`.

### 5.4. `InfographicsData`
- `goods_id`, `generated_images`, `enhanced_images`, `created_at`, `updated_at`.

### 5.5. `Report`
- `id`, `goods_id`, `user_id`, `seo_text`, `infographics`, `forecast_data` (JSON), `created_at`.

### 5.6. `PaymentTransaction`
- `id`, `user_id`, `order_id`, `provider_transaction_id`, `amount`, `currency`, `status`, `description`, `created_at`, `updated_at`.

## 6. Сервисы и бизнес-логика

### 6.1. `usage_service`
- **`get_user_usage(user_id)`** – возвращает `total_goods`, `seo_today`, `infographics_today`, `plan`, `plan_details`.
- **`check_limits(user_id, action, extra)`** – выбрасывает 403, если превышен лимит для действия (`add_goods`, `generate_seo`, `generate_infographics`, `enhance_infographics`). Использует конфиг `plans.py`.

### 6.2. `seo_service`
- **`generate_seo_for_goods(goods_id, user_id)`** – получает данные товара, вызывает GigaChat (или DeepSeek), сохраняет результат в `SeoData`, возвращает структуру.

### 6.3. `report_service`
- **`generate_report_data(goods_id, user_id)`** – строит промпт, вызывает GigaChat, парсит JSON, дополняет до 30 дней, сохраняет в `Report.forecast_data`.
- **`can_generate_report(goods_id, user_id, plan)`** – проверяет, прошло ли достаточно времени с последнего отчёта (cooldown).

### 6.4. `payment_service`
- `create_payment` – создаёт транзакцию в БД и вызывает провайдера (ЮKassa или заглушку).
- `handle_webhook` – обновляет статус по вебхуку.
- `get_transaction_status` – возвращает статус транзакции.

### 6.5. `image_enhancement_service`
- **`enhance_goods_images(goods_id, user_id)`** – скачивает до 4 изображений, создаёт коллаж, добавляет текстовую информацию, конвертирует в WebP, сохраняет в `InfographicsData.enhanced_images`.

## 7. Конфигурация тарифов (`plans.py`)

Каждый план содержит лимиты и фичи:
- `max_goods`
- `max_seo_per_day`
- `max_infographics_per_day` / `max_infographics_per_request` (генерация)
- `max_enhance_per_day` / `max_enhance_per_request` (улучшение)
- `report_cooldown_days`
- `support_level`, `api_access`, `priority_support`, `reports_format`
- `features_labels` – для фронтенда.

## 8. Интеграции

- **GigaChat** – через `GigaChatAPI.py` (синхронный клиент, обёрнутый в `asyncio.to_thread`). Методы: `getSEO`, `getResponseByPromt`.
- **ЮKassa** – через библиотеку `yookassa`. Настроена с ключами, поддерживает двухстадийную оплату. Включена заглушка.
- **Парсер Ozon** – `parser.py` загружает данные по URL, сохраняет во временную папку.

---