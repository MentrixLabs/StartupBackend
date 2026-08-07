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