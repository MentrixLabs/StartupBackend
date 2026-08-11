from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# ----- Категории (таблица ozon_item_categories) -----
class CategoryBase(BaseModel):
    category: str

class CategoryCreate(CategoryBase):
    item_id: int

class CategoryOut(CategoryBase):
    id: int
    item_id: int

    class Config:
        from_attributes = True

# ----- История (таблица ozon_item_history) -----
class HistoryBase(BaseModel):
    record_date: datetime
    price: Optional[float] = None
    rating: Optional[int] = None
    reviews_count: Optional[int] = None
    fbs_count: Optional[int] = None

class HistoryCreate(HistoryBase):
    item_id: int

class HistoryOut(HistoryBase):
    id: int
    item_id: int

    class Config:
        from_attributes = True

# ----- Отзывы (таблица ozon_item_feedbacks) -----
class FeedbackBase(BaseModel):
    feedback: str
    feedback_date: Optional[datetime] = None

class FeedbackCreate(FeedbackBase):
    item_id: int

class FeedbackOut(FeedbackBase):
    id: int
    item_id: int

    class Config:
        from_attributes = True


class SeoDataResponse(BaseModel):
    title: str
    description: str
    keywords: List[str]

class SeoCompetitorResponse(BaseModel):
    title: str
    description: str
    keywords: List[str]
    url: Optional[str] = None

class SeoHistoryResponse(BaseModel):
    generated: Optional[SeoDataResponse] = None
    summary: Optional[str] = None
    competitors: List[SeoCompetitorResponse] = []

class GoodsBase(BaseModel):
    name: str
    description: Optional[str] = None
    url: str

class GoodsCreate(GoodsBase):
    pass

class GoodsUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None

class GoodsOut(GoodsBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Все поля из парсера
    product_id: Optional[str] = None
    provider: Optional[str] = None
    brand: Optional[str] = None
    original_price: Optional[int] = None
    currency: Optional[str] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    main_imgs: Optional[List[str]] = None
    desc_imgs: Optional[List[str]] = None

    # Поля из связанных таблиц
    category: Optional[str] = None
    price: Optional[float] = None

    class Config:
        from_attributes = True