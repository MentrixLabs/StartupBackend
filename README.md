backend/
├── main.py                 # точка входа
├── core/
│   ├── config.py           # настройки (переиспользуем settings из config.py)
│   ├── security.py         # хэширование, JWT
│   └── dependencies.py     # зависимые элементы (например, get_current_user)
├── api/
│   ├── __init__.py
│   ├── auth.py             # регистрация, логин, профиль
│   ├── goods.py            # CRUD товаров
│   ├── seo.py              # генерация SEO
│   ├── infographics.py     # поиск инфографики
│   └── reports.py          # отчёты
├── schemas/
│   ├── __init__.py
│   ├── user.py             # Pydantic схемы для пользователей
│   ├── goods.py            # для товаров
│   └── common.py           # общие (ответы с ошибками и т.п.)
└── services/
    ├── __init__.py
    ├── seo_service.py      # вызов AI для SEO
    └── infographics_service.py  # поиск изображений