from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Date, Text, ARRAY
from sqlalchemy.orm import relationship
from db.db import Base

class OzonItem(Base):
    __tablename__ = "ozon_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    cardname = Column(String)
    description = Column(Text)
    url = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связи с другими таблицами (опционально, для удобства)
    categories = relationship("OzonItemCategory", back_populates="item")
    history = relationship("OzonItemHistory", back_populates="item")
    feedbacks = relationship("OzonItemFeedback", back_populates="item")


class OzonItemCategory(Base):
    __tablename__ = "ozon_item_categories"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("ozon_items.id"), nullable=False)
    category = Column(String, nullable=False)

    item = relationship("OzonItem", back_populates="categories")


class OzonItemHistory(Base):
    __tablename__ = "ozon_item_history"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("ozon_items.id"), nullable=False)
    record_date = Column(Date, nullable=False)
    price = Column(Float)
    rating = Column(Integer)
    reviews_count = Column(Integer)
    fbs_count = Column(Integer)

    item = relationship("OzonItem", back_populates="history")


class OzonItemFeedback(Base):
    __tablename__ = "ozon_item_feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("ozon_items.id"), nullable=False)
    feedback = Column(Text)
    feedback_date = Column(Date)

    item = relationship("OzonItem", back_populates="feedbacks")

class SeoData(Base):
    __tablename__ = "seo_data"

    goods_id = Column(Integer, ForeignKey("ozon_items.id"), primary_key=True, nullable=False)
    generated_title = Column(String(255), nullable=False)
    generated_description = Column(Text, nullable=False)
    generated_keywords = Column(ARRAY(String), nullable=False)
    summary = Column(Text)

class SeoCompetitor(Base):
    __tablename__ = "seo_competitors"

    id = Column(Integer, primary_key=True, index=True)
    goods_id = Column(Integer, ForeignKey("ozon_items.id"), nullable=False)
    competitor_title = Column(String(255), nullable=False)
    competitor_description = Column(Text, nullable=False)
    competitor_keywords = Column(ARRAY(String), nullable=False)
    competitor_url = Column(String(255), nullable=True)