from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={
        "timeout": 10,  # таймаут подключения к БД (сек)
        "command_timeout": 30,  # таймаут выполнения запроса (для asyncpg)
    }
)

async_session_maker = sessionmaker(
    engine,
    autocommit=False,
    autoflush=False,
    class_=AsyncSession,
    expire_on_commit=False,
    close_resets_only=False,
)


class Base(DeclarativeBase):
    pass
