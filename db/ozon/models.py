from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Date, Text, ARRAY, JSON
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

    # Новые поля из парсера
    product_id = Column(String(50))
    provider = Column(String(255))
    brand = Column(String(255))
    original_price = Column(Integer)
    currency = Column(String(10))
    rating = Column(Float)
    reviews_count = Column(Integer)
    main_imgs = Column(ARRAY(String))   # массив URL
    desc_imgs = Column(ARRAY(String))

    categories = relationship("OzonItemCategory", back_populates="item")
    history = relationship("OzonItemHistory", back_populates="item")
    feedbacks = relationship("OzonItemFeedback", back_populates="item")
    seo_data = relationship("SeoData", back_populates="item", uselist=False)
    infographics_data = relationship("InfographicsData", back_populates="item", uselist=False)
    reports = relationship("Report", back_populates="item")


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
    generated_title = Column(String(255))
    generated_description = Column(Text)
    generated_keywords = Column(ARRAY(String))
    summary = Column(Text)
    # Новые поля
    advertising_spend_ratio = Column(ARRAY(Float))  # массив [old, new]
    leads = Column(ARRAY(Float))                   # массив [old, new]
    ctr = Column(ARRAY(Float))                     # массив [old, new]
    created_at = Column(DateTime, default=datetime.utcnow)

    item = relationship("OzonItem", back_populates="seo_data")

class SeoCompetitor(Base):
    __tablename__ = "seo_competitors"

    id = Column(Integer, primary_key=True, index=True)
    goods_id = Column(Integer, ForeignKey("ozon_items.id"), nullable=False)
    competitor_title = Column(String(255), nullable=False)
    competitor_description = Column(Text, nullable=False)
    competitor_keywords = Column(ARRAY(String), nullable=False)
    competitor_url = Column(String(255), nullable=True)

class InfographicsData(Base):
    __tablename__ = "infographics_data"

    goods_id = Column(Integer, ForeignKey("ozon_items.id"), primary_key=True, nullable=False)
    generated_images = Column(ARRAY(String))   # массив URL/data-url сгенерированных изображений
    enhanced_images = Column(ARRAY(String))    # массив URL/data-url улучшенных изображений
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связь с товаром
    item = relationship("OzonItem", back_populates="infographics_data")

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    goods_id = Column(Integer, ForeignKey("ozon_items.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    seo_text = Column(Text, nullable=True)                # сгенерированный SEO-текст (если есть)
    infographics = Column(ARRAY(String), nullable=True)   # массив URL инфографики
    forecast_data = Column(JSON, nullable=True)           # данные прогнозов (JSON)

    # Связи
    item = relationship("OzonItem", back_populates="reports")


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    order_id = Column(String(64), unique=True, nullable=False)   # внутренний номер заказа
    provider_transaction_id = Column(String(64), nullable=True)  # ID транзакции у провайдера
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="RUB")
    status = Column(String(20), default="pending")  # pending, succeeded, canceled, refunded
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Связи
    user = relationship("User", back_populates="payments")