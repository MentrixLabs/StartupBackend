from db.dao.base import BaseDAO
from db.ozon.models import OzonItem, OzonItemCategory, OzonItemHistory, OzonItemFeedback, SeoData, SeoCompetitor

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