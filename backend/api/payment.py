# backend/api/payment.py
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from backend.core.dependencies import get_current_user
from db.user.models import User
from backend.services.payment_service import create_payment, handle_webhook, get_transaction_status

router = APIRouter(prefix="/payment", tags=["payment"])

class CreatePaymentRequest(BaseModel):
    amount: float
    description: Optional[str] = "Оплата услуги"

class PaymentResponse(BaseModel):
    order_id: str
    payment_id: str
    confirmation_url: str
    status: str

@router.post("/create", response_model=PaymentResponse)
async def create_payment_endpoint(
    req: CreatePaymentRequest,
    current_user: User = Depends(get_current_user)
):
    result = await create_payment(current_user.id, req.amount, req.description)
    return PaymentResponse(**result)

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
    """
    payload = await request.json()
    return await handle_webhook(payload)