from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from backend.api import auth, goods, seo, infographics, reports, stats
from db.db import engine
from db.dao.base import BaseDAO


app = FastAPI(
    title="Proskladai API",
    description="Бэкенд для автоматизации SEO и инфографики маркетплейсов",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # для локальной разработки
        "https://mentrixlabs.github.io",  # ваш GitHub Pages домен
        # Если у вас будет кастомный домен, добавьте его сюда
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(goods.router, prefix="/goods", tags=["goods"])
app.include_router(seo.router, prefix="/seo", tags=["seo"])
app.include_router(infographics.router, prefix="/infographics", tags=["infographics"])
app.include_router(reports.router)
app.include_router(stats.router)


@app.get("/")
async def root():
    return {"message": "Proskladai API is running"}