from db.dao.base import BaseDAO
from db.ozon.models import OzonItems

class OzonDAO(BaseDAO):
    model = OzonItems
