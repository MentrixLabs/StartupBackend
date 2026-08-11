from pydantic_settings import BaseSettings

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
    DEEPSEEK_API_KEY: str = ""
    YANDEX_CLOUD_FOLDER: str = ""
    YANDEX_CLOUD_API_KEY: str = ""
    YANDEX_CLOUD_MODEL: str = ""
    BASE_AI_URL: str  = ""

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"

settings = Settings()