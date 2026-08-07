from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import  ARRAY
from db.db import Base

class OzonItems(Base):
    __tablename__ = "ozon_items"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(ForeignKey('users.id'), nullable=False)
    cardnames = Column(ARRAY(String))
    urls_of_cards = Column(ARRAY(String))
    categories = Column(ARRAY(String))
    prices = Column(ARRAY(Integer, dimensions=2))
    dates = Column(ARRAY(String, dimensions=2))
    ratings = Column(ARRAY(Integer, dimensions=2))
    reviews_counts = Column(ARRAY(Integer, dimensions=2))
    descriptions = Column(ARRAY(String))
    feedbacks = Column(ARRAY(String))
