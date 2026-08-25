# backend/config/plans.py
from typing import Dict, Any

PLANS: Dict[str, Dict[str, Any]] = {
    "free": {
        # Лимиты
        "max_goods": 3,
        "max_seo_per_day": 1,
        "max_enhance_per_day": 1,
        "max_enhance_per_request": 1,
        "max_infographics_per_day": 0,
        "max_infographics_per_request": 0,
        "report_cooldown_days": 7,   # 1 раз в неделю
        # Фичи (доступность)
        "support_level": "email",          # email, phone, full
        "api_access": False,
        "priority_support": False,
        "reports_format": "basic",         # basic, pdf, pdf_excel
        # Для фронтенда (можно использовать как строки из features)
        "features_labels": {
            "До 3 товаров": True,
            "Генерация SEO (базовая, до 2 товаров в день)": True,
            "Создание инфографики (до 1 изображения)": True,
            "Базовые отчёты": True,
            "Поддержка в письмах": True,
            "API-доступ": False,
            "Приоритетная поддержка": False,
        }
    },
    "starter": {
        "max_goods": 50,
        "max_seo_per_day": 50,
        "max_enhance_per_day": 20,
        "max_enhance_per_request": 20,
        "max_infographics_per_day": 20,
        "max_infographics_per_request": 20,
        "report_cooldown_days": 3,   # 1 раз в 3 дня
        "support_level": "phone",
        "api_access": False,
        "priority_support": False,
        "reports_format": "pdf",
        "features_labels": {
            "До 50 товаров": True,
            "Генерация SEO (расширенная, до 50 товаров в день)": True,
            "Создание инфографики (до 20 изображений в день)": True,
            "Полные отчёты в PDF": True,
            "Поддержка 24/7 по телефону": True,
            "API-доступ": False,
            "Приоритетная поддержка": False,
        }
    },
    "business": {
        "max_goods": float('inf'),
        "max_seo_per_day": float('inf'),
        "max_enhance_per_day": 50,
        "max_enhance_per_request": 50,
        "max_infographics_per_day": 50,
        "max_infographics_per_request": 50,
        "report_cooldown_days": 1,   # 1 раз в день
        "support_level": "full",
        "api_access": True,
        "priority_support": True,
        "reports_format": "pdf_excel",
        "features_labels": {
            "Неограниченно товаров": True,
            "Генерация SEO (премиум, больше 50 товаров в день)": True,
            "Создание инфографики (до 50 изображений в день)": True,
            "Полные отчёты в PDF и Excel": True,
            "Поддержка 24/7": True,
            "API-доступ": True,
            "Приоритетная поддержка": True,
        }
    }
}

def get_plan_limits(plan: str) -> Dict[str, Any]:
    """Возвращает словарь с лимитами для плана."""
    return PLANS.get(plan, PLANS["free"])

def get_plan_details(plan: str) -> Dict[str, Any]:
    """Возвращает полную информацию о плане (включая фичи)."""
    return PLANS.get(plan, PLANS["free"])