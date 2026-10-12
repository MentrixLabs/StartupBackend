# База данных для аналитики Ozon

Система для управления пользовательскими данными и аналитикой товаров с Ozon. 
База данных использует SQLAlchemy с асинхронным режимом работы.

`pip install sqlalchemy asyncpg fastapi`

## Структура базы данных

### Таблица `UserData`
| Поле                | Тип          | Описание                       |
|---------------------|--------------|--------------------------------|
| id                  | Integer      | Уникальный идентификатор       |
| username            | String       | Имя пользователя (уникальное)  |
| telegram_name       | String       | Телеграм-юзернейм              |
| date_of_birth       | Integer      | Дата рождения (timestamp)      |
| region              | String       | Регион проживания              |
| sex                 | String       | Пол                            |
| api_key_ozon        | String       | API-ключ Ozon                  |
| client_id_ozon      | Integer      | Client ID Ozon                 |
| identify_of_stock   | String       | Идентификатор склада           |
| count_of_stocks     | Integer      | Количество складов             |
| provider_id         | Integer      | ID провайдера                  |
   
### Таблица `OzonData`   
| Поле           | Тип            | Описание                          |
|----------------|----------------|-----------------------------------|
| id             | Integer        | Уникальный идентификатор          |
| username       | String         | Связь с пользователем             |
| cardname       | String         | Название карточки товара          |
| url_of_card    | String         | URL карточки                      |
| category       | String         | Категория товара                  |
| price          | ARRAY(Integer) | Динамика цен (история изменений)  |
| date           | ARRAY(String)  | Даты обновлений                   |
| rating         | ARRAY(Integer) | История рейтингов                 |
| reviews_count  | ARRAY(Integer) | История количества отзывов        |
| description    | String         | Описание товара                   |
| feedbacks      | JSONB          | Отзывы в формате JSON             |
   
## Основные функции

### 1. Управление пользователями
```python```
async def create_or_update_user(**kwargs)

### 2. Управление данными Ozon
```python```
async def update_or_create_ozon_data(**kwargs)

### Выполнение миграций
######Подготовка файла миграций
Теперь, чтобы подготовить файл миграций, создадим инструкцию для Alembic, которая будет использоваться для создания таблиц. В терминале выполните следующую команду:
```terminal```
alembic revision --autogenerate -m "Initial revision"

######Обновление базы данных до последней версии миграции
Для того чтобы обновить базу данных до последней версии, выполните команду:
```terminal```
alembic upgrade head

######Откат на одну версию назад
Чтобы откатить миграцию на одну версию назад, используйте следующую команду:
```terminal```
alembic downgrade -1

######Откат до конкретной миграции
Если вам нужно откатить базу данных до определенной миграции, укажите ID этой миграции (аналогично для миграции конкретного пользователя - в конце добавляется ID):
```terminal```
alembic downgrade d97a9824423b

### Поднять базу данных

```SQL```
-- ============================================================
-- Инициализация БД ProSkladDB для проекта Proskladai
-- Порядок создания таблиц учитывает зависимости FK.
-- ============================================================

-- ============================================================
-- 1. users
-- ============================================================
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR NOT NULL UNIQUE,
    email VARCHAR NOT NULL UNIQUE,
    tg_id BIGINT UNIQUE,
    hashed_password VARCHAR NOT NULL,
    plan VARCHAR(20) NOT NULL DEFAULT 'free'
);
CREATE INDEX ix_users_id ON users(id);

-- ============================================================
-- 2. profiles
-- ============================================================
CREATE TABLE profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
    date_of_birth DATE,
    region VARCHAR,
    sex BOOLEAN,
    api_key_ozon VARCHAR UNIQUE,
    client_id_ozon INTEGER UNIQUE,
    provider_id INTEGER
);
CREATE INDEX ix_profiles_id ON profiles(id);
CREATE INDEX ix_profiles_user_id ON profiles(user_id);

-- ============================================================
-- 3. ozon_items
-- ============================================================
CREATE TABLE ozon_items (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    cardname VARCHAR,
    description TEXT,
    url VARCHAR NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
    product_id VARCHAR(50),
    provider VARCHAR(255),
    brand VARCHAR(255),
    original_price INTEGER,
    currency VARCHAR(10),
    rating DOUBLE PRECISION,
    reviews_count INTEGER,
    main_imgs TEXT[],
    desc_imgs TEXT[]
);
CREATE INDEX ix_ozon_items_id ON ozon_items(id);
CREATE INDEX ix_ozon_items_user_id ON ozon_items(user_id);

-- ============================================================
-- 4. ozon_item_categories
-- ============================================================
CREATE TABLE ozon_item_categories (
    id SERIAL PRIMARY KEY,
    item_id INTEGER NOT NULL REFERENCES ozon_items(id) ON DELETE CASCADE,
    category VARCHAR NOT NULL
);
CREATE INDEX ix_ozon_item_categories_id ON ozon_item_categories(id);
CREATE INDEX ix_ozon_item_categories_item_id ON ozon_item_categories(item_id);

-- ============================================================
-- 5. ozon_item_history
-- ============================================================
CREATE TABLE ozon_item_history (
    id SERIAL PRIMARY KEY,
    item_id INTEGER NOT NULL REFERENCES ozon_items(id) ON DELETE CASCADE,
    record_date DATE NOT NULL,
    price DOUBLE PRECISION,
    rating INTEGER,
    reviews_count INTEGER,
    fbs_count INTEGER
);
CREATE INDEX ix_ozon_item_history_id ON ozon_item_history(id);
CREATE INDEX ix_ozon_item_history_item_id ON ozon_item_history(item_id);

-- ============================================================
-- 6. ozon_item_feedbacks
-- ============================================================
CREATE TABLE ozon_item_feedbacks (
    id SERIAL PRIMARY KEY,
    item_id INTEGER NOT NULL REFERENCES ozon_items(id) ON DELETE CASCADE,
    feedback TEXT,
    feedback_date DATE
);
CREATE INDEX ix_ozon_item_feedbacks_id ON ozon_item_feedbacks(id);
CREATE INDEX ix_ozon_item_feedbacks_item_id ON ozon_item_feedbacks(item_id);

-- ============================================================
-- 7. seo_data
-- ============================================================
CREATE TABLE seo_data (
    goods_id INTEGER PRIMARY KEY NOT NULL REFERENCES ozon_items(id) ON DELETE CASCADE,
    generated_title VARCHAR(255),
    generated_description TEXT,
    generated_keywords TEXT[],
    summary TEXT,
    advertising_spend_ratio DOUBLE PRECISION[],
    leads DOUBLE PRECISION[],
    ctr DOUBLE PRECISION[],
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now()
);

-- ============================================================
-- 8. seo_competitors
-- ============================================================
CREATE TABLE seo_competitors (
    id SERIAL PRIMARY KEY,
    goods_id INTEGER NOT NULL REFERENCES ozon_items(id) ON DELETE CASCADE,
    competitor_title VARCHAR(255) NOT NULL,
    competitor_description TEXT NOT NULL,
    competitor_keywords TEXT[] NOT NULL,
    competitor_url VARCHAR(255)
);
CREATE INDEX ix_seo_competitors_id ON seo_competitors(id);
CREATE INDEX ix_seo_competitors_goods_id ON seo_competitors(goods_id);

-- ============================================================
-- 9. infographics_data
-- ============================================================
CREATE TABLE infographics_data (
    goods_id INTEGER PRIMARY KEY NOT NULL REFERENCES ozon_items(id) ON DELETE CASCADE,
    generated_images TEXT[],
    enhanced_images TEXT[],
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now()
);

-- ============================================================
-- 10. reports
-- ============================================================
CREATE TABLE reports (
    id SERIAL PRIMARY KEY,
    goods_id INTEGER NOT NULL REFERENCES ozon_items(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
    seo_text TEXT,
    infographics TEXT[],
    forecast_data JSONB
);
CREATE INDEX ix_reports_id ON reports(id);
CREATE INDEX ix_reports_goods_id ON reports(goods_id);
CREATE INDEX ix_reports_user_id ON reports(user_id);

-- ============================================================
-- 11. payment_transactions
-- ============================================================
CREATE TABLE payment_transactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    order_id VARCHAR(64) NOT NULL UNIQUE,
    provider_transaction_id VARCHAR(64),
    amount DOUBLE PRECISION NOT NULL,
    currency VARCHAR(3) DEFAULT 'RUB',
    status VARCHAR(20) DEFAULT 'pending',
    description TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now()
);
CREATE INDEX ix_payment_transactions_id ON payment_transactions(id);
CREATE INDEX ix_payment_transactions_user_id ON payment_transactions(user_id);
CREATE INDEX ix_payment_transactions_order_id ON payment_transactions(order_id);

-- ============================================================
-- Проверка: список созданных таблиц
-- ============================================================
-- SELECT table_name FROM information_schema.tables
-- WHERE table_schema = 'public' ORDER BY table_name;