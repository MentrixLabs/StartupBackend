from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    JWT_KEY: str
    JWT_ALG: str
    MODE: str = "DEV"
    TELEGRAM_BOT_TOKEN: str = ""
    OZON_API_KEY: str = ""
    CLIENT_ID: int = 0
    YANDEX_CLOUD_FOLDER: str = ""
    YANDEX_CLOUD_API_KEY: str = ""
    YANDEX_CLOUD_MODEL: str = ""
    BASE_AI_URL: str  = ""
    DEEPSEEK_API_KEY: str = YANDEX_CLOUD_API_KEY
    SBER_CLIENT_ID: str = ""
    SBER_SCOPE: str = ""
    SBER_AUTHORIZATION_KEY: str = ""
    SBER_CLIENT_SECRET: str = ""
    YOOKASSA_SHOP_ID: str = ""
    YOOKASSA_SECRET_KEY: str = ""
    YOOKASSA_RETURN_URL: str = "https://mentrixlabs.github.io/payment-success"
    PAYMENT_MOCK_ENABLED: bool = os.getenv("PAYMENT_MOCK_ENABLED", "False").lower() == "true"

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"

settings = Settings()