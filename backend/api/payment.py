# backend/api/payment.py
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List
from backend.core.dependencies import get_current_user
from db.user.models import User
from backend.services.payment_service import (
    create_payment,
    handle_webhook,
    get_transaction_status,
    capture_payment,          # уже есть в сервисе
    create_receipt,           # новая функция (будет добавлена)
)
from backend.services.payment_service import payment_provider  # для прямого вызова, если не добавить функцию

router = APIRouter(prefix="/payment", tags=["payment"])

# --- Модели ---

class CreatePaymentRequest(BaseModel):
    amount: float
    description: Optional[str] = "Оплата услуги"

class PaymentResponse(BaseModel):
    order_id: str
    payment_id: str
    confirmation_url: str
    status: str

# Модель для позиции чека
class ReceiptItem(BaseModel):
    description: str          # наименование товара
    quantity: float           # количество
    amount: float             # цена за единицу
    vat_code: int = 1         # ставка НДС (1 – 18%, 2 – 10%, 3 – 0% и т.д.)

# Запрос на создание чека
class CreateReceiptRequest(BaseModel):
    order_id: str
    items: List[ReceiptItem]
    email: Optional[str] = None  # если не передано, берётся из current_user

# Запрос на захват платежа
class CapturePaymentRequest(BaseModel):
    order_id: str

# --- Эндпоинты ---

@router.post("/create", response_model=PaymentResponse)
async def create_payment_endpoint(
    req: CreatePaymentRequest,
    current_user: User = Depends(get_current_user)
):
    result = await create_payment(current_user.id, req.amount, req.description)
    return PaymentResponse(**result)

@router.post("/capture")
async def capture_payment_endpoint(
    req: CapturePaymentRequest,
    current_user: User = Depends(get_current_user)
):
    """Подтверждение платежа (захват) перед созданием чека."""
    return await capture_payment(req.order_id, current_user.id)

@router.post("/receipt")
async def create_receipt_endpoint(
    req: CreateReceiptRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Создание фискального чека для уже успешно проведённого платежа.
    Обычно вызывается после /capture.
    """
    email = req.email or current_user.email
    if not email:
        raise HTTPException(400, "Email покупателя обязателен")

    items_data = [item.dict() for item in req.items]
    result = await create_receipt(
        order_id=req.order_id,
        user_id=current_user.id,
        items=items_data,
        email=email
    )
    return result

@router.get("/status/{order_id}")
async def get_payment_status(
    order_id: str,
    current_user: User = Depends(get_current_user)
):
    return await get_transaction_status(order_id, current_user.id)

@router.post("/webhook")
async def payment_webhook(request: Request):
    """
    Вебхук от платёжной системы (например, ЮKassa).
    Здесь также можно автоматически создавать чек, если состав заказа сохранён заранее.
    """
    payload = await request.json()
    return await handle_webhook(payload)