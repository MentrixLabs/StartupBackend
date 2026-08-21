from db.dao.base import BaseDAO
from db.ozon.models import OzonItem, OzonItemCategory, OzonItemHistory, OzonItemFeedback, SeoData, SeoCompetitor, InfographicsData, Report, PaymentTransaction
from db.db import async_session_maker
from sqlalchemy import select


class OzonItemDAO(BaseDAO):
    model = OzonItem

class OzonItemCategoryDAO(BaseDAO):
    model = OzonItemCategory

class OzonItemHistoryDAO(BaseDAO):
    model = OzonItemHistory

class OzonItemFeedbackDAO(BaseDAO):
    model = OzonItemFeedback

class SeoDataDAO(BaseDAO):
    model = SeoData

    # Если `update` ожидает `id`, переопределите:
    @classmethod
    async def update(cls, goods_id: int, **data):
        async with async_session_maker() as session:
            instance = await cls.find_one_or_none(goods_id=goods_id)
            if instance:
                for key, value in data.items():
                    setattr(instance, key, value)
                await session.commit()
                return instance
            return None

class SeoCompetitorDAO(BaseDAO):
    model = SeoCompetitor

class InfographicsDataDAO(BaseDAO):
    model = InfographicsData

class ReportDAO(BaseDAO):
    model = Report

@classmethod
async def delete(cls, **filter_by):
    async with async_session_maker() as session:
        instance = await cls.find_one_or_none(**filter_by)
        if instance:
            await session.delete(instance)
            await session.commit()
            return True
        return False

class PaymentTransactionDAO(BaseDAO):
    model = PaymentTransaction

class OzonItemHistoryDAO(BaseDAO):
    model = OzonItemHistory

    @classmethod
    async def upsert_stock(cls, item_id: int, record_date, fbs_count: int):
        """Обновить или создать запись истории с указанным fbs_count для товара и даты."""
        async with async_session_maker() as session:
            # Проверяем существование
            existing = await session.execute(
                select(cls.model).where(
                    cls.model.item_id == item_id,
                    cls.model.record_date == record_date
                )
            )
            existing = existing.scalar_one_or_none()
            if existing:
                # Обновляем только fbs_count, остальные поля оставляем как есть
                existing.fbs_count = fbs_count
                await session.commit()
                return existing
            else:
                # Создаём новую запись (другие поля можно оставить NULL)
                new_record = cls.model(
                    item_id=item_id,
                    record_date=record_date,
                    fbs_count=fbs_count,
                    price=None,          # или можно взять последнюю цену, но пока NULL
                    rating=None,
                    reviews_count=None
                )
                session.add(new_record)
                await session.commit()
                await session.refresh(new_record)
                return new_record