# backend/services/payment_service.py
import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from db.db import async_session_maker
from db.ozon.dao import PaymentTransactionDAO
from config import settings

# Импорты из библиотеки yookassa
from yookassa import Configuration, Payment, Refund, Receipt
from yookassa.domain.models.amount import Amount
from yookassa.domain.request.payment_request import PaymentRequest
from yookassa.domain.request.refund_request import RefundRequest
from yookassa.domain.request.receipt_request import ReceiptRequest
from yookassa.domain.models.receipt import ReceiptItem, ReceiptCustomer

logger = logging.getLogger(__name__)

# Настройка ЮKassa (выполняется один раз при старте приложения)
def configure_yookassa():
    Configuration.account_id = settings.YOOKASSA_SHOP_ID
    Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

configure_yookassa()

class YooKassaProvider:
    """Реализация платежного провайдера ЮKassa."""

    async def create_payment(
        self,
        amount: float,
        description: str,
        order_id: str,
        user_id: int,
        capture: bool = False,
        items: Optional[List[Dict[str, Any]]] = None,
        email: Optional[str] = None,
    ) -> Dict[str, Any]:
        if settings.PAYMENT_MOCK_ENABLED:
            logger.info(f"MOCK: Creating payment for order {order_id}, amount {amount}")
            return {
                "payment_id": f"mock-{uuid.uuid4().hex[:8]}",
                "confirmation_url": "https://yoomoney.ru/pay",
                "status": "pending",
                "created_at": datetime.utcnow().isoformat(),
            }

        payment_request = PaymentRequest()
        payment_request.amount = Amount(value=amount, currency="RUB")
        payment_request.description = description
        payment_request.capture = capture
        payment_request.confirmation = {
            "type": "redirect",
            "return_url": settings.YOOKASSA_RETURN_URL or "https://mentrixlabs.github.io/payment-success"
        }
        payment_request.metadata = {
            "order_id": order_id,
            "user_id": str(user_id),
        }

        # Добавляем чек, если переданы товары и email
        if items and email:
            receipt_data = {
                "customer": {"email": email},
                "tax_system_code": 1,  # ОСН, можно изменить при необходимости
                "items": [
                    {
                        "description": item["description"],
                        "quantity": float(item["quantity"]),
                        "amount": {"value": float(item["amount"]), "currency": "RUB"},
                        "vat_code": item.get("vat_code", 1)
                    }
                    for item in items
                ]
            }
            payment_request.receipt = receipt_data

        import asyncio
        payment = await asyncio.to_thread(Payment.create, payment_request, uuid.uuid4())

        return {
            "payment_id": payment.id,
            "confirmation_url": payment.confirmation.confirmation_url,
            "status": payment.status,
            "created_at": payment.created_at,
        }

    async def capture_payment(self, payment_id: str, amount: float = None) -> Dict[str, Any]:
        import asyncio
        if amount is not None:
            capture_amount = Amount(value=amount, currency="RUB")
            payment = await asyncio.to_thread(Payment.capture, payment_id, {"amount": capture_amount}, uuid.uuid4())
        else:
            payment = await asyncio.to_thread(Payment.capture, payment_id, {}, uuid.uuid4())
        return {"status": payment.status, "captured_at": payment.captured_at}

    async def cancel_payment(self, payment_id: str) -> Dict[str, Any]:
        import asyncio
        payment = await asyncio.to_thread(Payment.cancel, payment_id, uuid.uuid4())
        return {"status": payment.status}

    async def get_payment_info(self, payment_id: str) -> Dict[str, Any]:
        import asyncio
        payment = await asyncio.to_thread(Payment.find_one, payment_id)
        return {
            "id": payment.id,
            "status": payment.status,
            "amount": payment.amount.value,
            "currency": payment.amount.currency,
            "paid": payment.paid,
            "refundable": payment.refundable,
            "created_at": payment.created_at,
            "captured_at": getattr(payment, "captured_at", None),
            "description": payment.description,
            "metadata": payment.metadata,
        }

    async def create_refund(
        self,
        payment_id: str,
        amount: float,
        description: str = "Возврат средств",
    ) -> Dict[str, Any]:
        import asyncio
        refund_request = RefundRequest()
        refund_request.payment_id = payment_id
        refund_request.amount = Amount(value=amount, currency="RUB")
        refund_request.description = description
        refund = await asyncio.to_thread(Refund.create, refund_request, uuid.uuid4())
        return {"refund_id": refund.id, "status": refund.status, "created_at": refund.created_at}

    # ----- Новый метод для создания чека -----
    async def create_receipt(self, payment_id: str, email: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Отправляет запрос в ЮKassa на создание фискального чека для уже успешного платежа.
        """
        import asyncio

        # Преобразуем элементы в объекты ReceiptItem
        receipt_items = []
        for item in items:
            receipt_items.append(
                ReceiptItem(
                    description=item["description"],
                    quantity=item["quantity"],
                    amount=Amount(value=item["amount"], currency="RUB"),
                    vat_code=item.get("vat_code", 1)
                )
            )

        customer = ReceiptCustomer(email=email)

        receipt_request = ReceiptRequest(
            payment_id=payment_id,
            items=receipt_items,
            customer=customer,
            send=True,  # Отправить чек покупателю на email
            settlement=[]  # При необходимости можно добавить данные о рассчётах
        )

        receipt = await asyncio.to_thread(Receipt.create, receipt_request, uuid.uuid4())

        return {
            "receipt_id": receipt.id,
            "status": receipt.status,
            "registered_at": getattr(receipt, "registered_at", None),
        }

    async def handle_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        event = payload.get("event")
        if not event:
            raise HTTPException(400, "Missing event field")

        payment_data = payload.get("object")
        if not payment_data:
            raise HTTPException(400, "Missing payment object")

        payment_id = payment_data.get("id")
        status = payment_data.get("status")
        metadata = payment_data.get("metadata", {})
        order_id = metadata.get("order_id")
        if not order_id:
            logger.error("order_id not found in metadata")
            return {"status": "error", "message": "order_id missing"}

        async with async_session_maker() as session:
            transaction = await PaymentTransactionDAO.find_one_or_none(order_id=order_id)
            if not transaction:
                logger.warning(f"Transaction for order {order_id} not found")
                return {"status": "error", "message": "transaction not found"}

            new_status = self._map_yookassa_status(status)
            if new_status and new_status != transaction.status:
                await PaymentTransactionDAO.update(
                    transaction.id,
                    status=new_status,
                    provider_transaction_id=payment_id,
                    updated_at=datetime.utcnow(),
                )
                logger.info(f"Transaction {order_id} updated to {new_status}")

        return {"status": "ok"}

    @staticmethod
    def _map_yookassa_status(yk_status: str) -> str:
        mapping = {
            "pending": "pending",
            "waiting_for_capture": "pending",
            "succeeded": "succeeded",
            "canceled": "canceled",
        }
        return mapping.get(yk_status, "pending")


# Создаем экземпляр провайдера
payment_provider = YooKassaProvider()


# --- Публичные функции (используются в API) ---

async def create_payment(
    user_id: int,
    amount: float,
    description: str = "Оплата услуги",
    items: Optional[List[Dict[str, Any]]] = None,
    email: Optional[str] = None,
) -> Dict[str, Any]:
    order_id = f"ORDER-{user_id}-{uuid.uuid4().hex[:8]}"

    async with async_session_maker() as session:
        await PaymentTransactionDAO.add(
            user_id=user_id,
            order_id=order_id,
            amount=amount,
            status="pending",
            description=description,
        )

    try:
        result = await payment_provider.create_payment(
            amount=amount,
            description=description,
            order_id=order_id,
            user_id=user_id,
            capture=False,
            items=items,
            email=email,
        )
        async with async_session_maker() as session:
            transaction = await PaymentTransactionDAO.find_one_or_none(order_id=order_id)
            if transaction:
                await PaymentTransactionDAO.update(
                    transaction.id,
                    provider_transaction_id=result["payment_id"],
                )
        return {
            "order_id": order_id,
            "payment_id": result["payment_id"],
            "confirmation_url": result["confirmation_url"],
            "status": result["status"],
        }
    except Exception as e:
        logger.error(f"Payment creation failed: {e}", exc_info=True)
        async with async_session_maker() as session:
            transaction = await PaymentTransactionDAO.find_one_or_none(order_id=order_id)
            if transaction:
                await PaymentTransactionDAO.update(transaction.id, status="failed")
        raise HTTPException(500, f"Payment creation failed: {str(e)}")


async def capture_payment(order_id: str, user_id: int) -> Dict[str, Any]:
    async with async_session_maker() as session:
        transaction = await PaymentTransactionDAO.find_one_or_none(order_id=order_id, user_id=user_id)
        if not transaction:
            raise HTTPException(404, "Transaction not found")
        if transaction.status != "pending":
            raise HTTPException(400, "Transaction is not pending")
        payment_id = transaction.provider_transaction_id
        if not payment_id:
            raise HTTPException(400, "No provider transaction id")

    try:
        result = await payment_provider.capture_payment(payment_id)
        async with async_session_maker() as session:
            await PaymentTransactionDAO.update(
                transaction.id,
                status="succeeded",
                updated_at=datetime.utcnow(),
            )
        return {"status": "succeeded", "captured_at": result.get("captured_at")}
    except Exception as e:
        logger.error(f"Payment capture failed: {e}", exc_info=True)
        raise HTTPException(500, f"Capture failed: {str(e)}")


async def cancel_payment(order_id: str, user_id: int) -> Dict[str, Any]:
    async with async_session_maker() as session:
        transaction = await PaymentTransactionDAO.find_one_or_none(order_id=order_id, user_id=user_id)
        if not transaction:
            raise HTTPException(404, "Transaction not found")
        if transaction.status != "pending":
            raise HTTPException(400, "Transaction is not pending")
        payment_id = transaction.provider_transaction_id
        if not payment_id:
            raise HTTPException(400, "No provider transaction id")

    try:
        result = await payment_provider.cancel_payment(payment_id)
        async with async_session_maker() as session:
            await PaymentTransactionDAO.update(
                transaction.id,
                status="canceled",
                updated_at=datetime.utcnow(),
            )
        return {"status": "canceled"}
    except Exception as e:
        logger.error(f"Payment cancel failed: {e}", exc_info=True)
        raise HTTPException(500, f"Cancel failed: {str(e)}")


async def get_transaction_status(order_id: str, user_id: int) -> Dict[str, Any]:
    """Получить статус транзакции из БД."""
    async with async_session_maker() as session:
        transaction = await PaymentTransactionDAO.find_one_or_none(order_id=order_id, user_id=user_id)
        if not transaction:
            raise HTTPException(404, "Transaction not found")
        return {
            "order_id": transaction.order_id,
            "status": transaction.status,
            "amount": transaction.amount,
            "created_at": transaction.created_at.isoformat(),
            "description": transaction.description,
        }


async def handle_webhook(payload: Dict[str, Any]) -> Dict[str, Any]:
    return await payment_provider.handle_webhook(payload)


async def create_refund(order_id: str, user_id: int, amount: float, description: str = "Возврат средств") -> Dict[str, Any]:
    async with async_session_maker() as session:
        transaction = await PaymentTransactionDAO.find_one_or_none(order_id=order_id, user_id=user_id)
        if not transaction:
            raise HTTPException(404, "Transaction not found")
        if transaction.status != "succeeded":
            raise HTTPException(400, "Transaction is not succeeded")
        payment_id = transaction.provider_transaction_id
        if not payment_id:
            raise HTTPException(400, "No provider transaction id")

    try:
        result = await payment_provider.create_refund(payment_id, amount, description)
        logger.info(f"Refund created for payment {payment_id}: {result}")
        return result
    except Exception as e:
        logger.error(f"Refund creation failed: {e}", exc_info=True)
        raise HTTPException(500, f"Refund failed: {str(e)}")


# --- Новая публичная функция для создания чека ---
async def create_receipt(order_id: str, user_id: int, items: List[Dict[str, Any]], email: str) -> Dict[str, Any]:
    """
    Создаёт фискальный чек для успешного платежа.
    Транзакция должна иметь статус 'succeeded'.
    """
    async with async_session_maker() as session:
        transaction = await PaymentTransactionDAO.find_one_or_none(order_id=order_id, user_id=user_id)
        if not transaction:
            raise HTTPException(404, "Transaction not found")
        if transaction.status != "succeeded":
            raise HTTPException(400, "Transaction not succeeded, cannot create receipt")
        payment_id = transaction.provider_transaction_id
        if not payment_id:
            raise HTTPException(400, "No provider transaction id")

    try:
        # Подготавливаем элементы чека в формате, который ожидает провайдер
        receipt_items = []
        for item in items:
            receipt_items.append({
                "description": item["description"],
                "quantity": item["quantity"],
                "amount": item["amount"],
                "vat_code": item.get("vat_code", 1)
            })

        result = await payment_provider.create_receipt(
            payment_id=payment_id,
            email=email,
            items=receipt_items
        )
        logger.info(f"Receipt created for payment {payment_id}: {result}")
        return result
    except Exception as e:
        logger.error(f"Receipt creation failed: {e}", exc_info=True)
        raise HTTPException(500, f"Receipt creation failed: {str(e)}")