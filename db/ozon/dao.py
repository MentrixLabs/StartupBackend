from db.dao.base import BaseDAO
from db.ozon.models import OzonItem, OzonItemCategory, OzonItemHistory, OzonItemFeedback, SeoData, SeoCompetitor
from db.db import async_session_maker

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

class SeoCompetitorDAO(BaseDAO):
    model = SeoCompetitor

@classmethod
async def delete(cls, **filter_by):
    async with async_session_maker() as session:
        instance = await cls.find_one_or_none(**filter_by)
        if instance:
            await session.delete(instance)
            await session.commit()
            return True
        return False