import uvicorn
from backend.main import app
import subprocess
import sys

# Устанавливаем браузеры Playwright при первом запуске
subprocess.run([sys.executable, "-m", "playwright", "install", "--with-deps", "chromium"])

# ... остальной код вашего приложения

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000
        
    )