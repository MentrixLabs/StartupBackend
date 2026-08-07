# core/config.py
import sys
from pathlib import Path
# Добавляем путь к корню проекта
sys.path.append(str(Path(__file__).parent.parent))
from config import settings  # ваш существующий объект Settings

__all__ = ["settings"]