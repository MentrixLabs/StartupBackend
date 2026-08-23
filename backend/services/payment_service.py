# backend/services/payment_service.py
import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from db.db import async_session_maker
from db.ozon.dao import PaymentTransactionDAO
from config import settings

# Импортируем клиент ЮKassa
from yookassa import Configuration, Payment, Refund, Receipt
from yookassa.domain.response.payment_response import PaymentResponse
from yookassa.domain.response.refund_response import RefundResponse
from yookassa.domain.response.receipt_response import ReceiptResponse
from yookassa.domain.models.amount import Amount
from yookassa.domain.models.confirmation import ConfirmationRedirect
from yookassa.domain.request.payment_request import PaymentRequest
from yookassa.domain.request.refund_request import RefundRequest
from yookassa.domain.request.receipt_request import ReceiptRequest
from yookassa.domain.models.receipt import ReceiptItem, ReceiptCustomer

logger = logging.getLogger(__name__)

# Настройка ЮKassa (выполняется один раз при старте приложения)
def configure_yookassa():
    Configuration.account_id = settings.YOOKASSA_SHOP_ID
    Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

# Вызываем конфигурацию при импорте (или можно вызвать в main.py)
configure_yookassa()

class YooKassaProvider:
    async def create_payment(self, amount: float, description: str, order_id: str, user_id: int) -> Dict[str, Any]:
        # Имитация успешного создания платежа
        return {
            "payment_id": f"test-{uuid.uuid4().hex[:8]}",
            "confirmation_url": "https://yoomoney.ru/pay",  # тестовая ссылка
            "status": "pending",
        }
    
class TrueYooKassaProvider:
    """Реализация платежного провайдера ЮKassa."""

    async def create_payment(
        self,
        amount: float,
        description: str,
        order_id: str,
        user_id: int,
        capture: bool = False,  # True – одностадийная оплата, False – двухстадийная
    ) -> Dict[str, Any]:
        """
        Создает платеж в ЮKassa.
        """
        # Формируем запрос
        payment_request = PaymentRequest()
        payment_request.amount = Amount(value=amount, currency="RUB")
        payment_request.description = description
        payment_request.capture = capture  # если False, нужно будет подтверждать
        payment_request.confirmation = ConfirmationRedirect(
            return_url=settings.YOOKASSA_RETURN_URL or "https://mentrixlabs.github.io/payment-success"
        )
        payment_request.metadata = {
            "order_id": order_id,
            "user_id": str(user_id),
        }

        # Создаем платеж (синхронный вызов, поэтому оборачиваем в to_thread)
        import asyncio
        payment = await asyncio.to_thread(Payment.create, payment_request, uuid.uuid4())

        return {
            "payment_id": payment.id,
            "confirmation_url": payment.confirmation.confirmation_url,
            "status": payment.status,
            "created_at": payment.created_at,
        }

    async def capture_payment(self, payment_id: str, amount: float = None) -> Dict[str, Any]:
        """Подтверждает платеж (для двухстадийной оплаты)."""
        import asyncio
        if amount is not None:
            capture_amount = Amount(value=amount, currency="RUB")
            payment = await asyncio.to_thread(Payment.capture, payment_id, {"amount": capture_amount}, uuid.uuid4())
        else:
            payment = await asyncio.to_thread(Payment.capture, payment_id, {}, uuid.uuid4())
        return {"status": payment.status, "captured_at": payment.captured_at}

    async def cancel_payment(self, payment_id: str) -> Dict[str, Any]:
        """Отменяет платеж (только в статусе waiting_for_capture)."""
        import asyncio
        payment = await asyncio.to_thread(Payment.cancel, payment_id, uuid.uuid4())
        return {"status": payment.status}

    async def get_payment_info(self, payment_id: str) -> Dict[str, Any]:
        """Получает информацию о платеже."""
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
        """Создает возврат по платежу."""
        import asyncio
        refund_request = RefundRequest()
        refund_request.payment_id = payment_id
        refund_request.amount = Amount(value=amount, currency="RUB")
        refund_request.description = description
        refund = await asyncio.to_thread(Refund.create, refund_request, uuid.uuid4())
        return {"refund_id": refund.id, "status": refund.status, "created_at": refund.created_at}

    async def create_receipt(
        self,
        payment_id: str,
        email: str,
        items: list,
        settlement_type: str = "cashless",
    ) -> Dict[str, Any]:
        """
        Создает чек для платежа.
        items: список словарей с полями description, quantity, amount, vat_code.
        """
        import asyncio
        receipt_items = []
        for item in items:
            receipt_item = ReceiptItem()
            receipt_item.description = item["description"]
            receipt_item.quantity = item["quantity"]
            receipt_item.amount = Amount(value=item["amount"], currency="RUB")
            receipt_item.vat_code = item.get("vat_code", 1)
            receipt_items.append(receipt_item)

        customer = ReceiptCustomer()
        customer.email = email

        receipt_request = ReceiptRequest()
        receipt_request.payment_id = payment_id
        receipt_request.items = receipt_items
        receipt_request.customer = customer
        receipt_request.settlements = [{"type": settlement_type, "amount": Amount(value=sum(i["amount"] * i["quantity"] for i in items), currency="RUB")}]

        receipt = await asyncio.to_thread(Receipt.create, receipt_request, uuid.uuid4())
        return {"receipt_id": receipt.id, "status": receipt.status}

    async def handle_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обрабатывает входящие уведомления от ЮKassa.
        Обновляет статус транзакции в нашей БД.
        """
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

        # Обновляем статус в БД
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
            "waiting_for_capture": "pending",  # для нас пока pending
            "succeeded": "succeeded",
            "canceled": "canceled",
        }
        return mapping.get(yk_status, "pending")


# Создаем экземпляр провайдера
payment_provider = YooKassaProvider()


# --- Публичные функции сервиса (используются в API) ---

async def create_payment(
    user_id: int,
    amount: float,
    description: str = "Оплата услуги",
) -> Dict[str, Any]:
    """Создает платеж и сохраняет транзакцию в БД."""
    order_id = f"ORDER-{user_id}-{uuid.uuid4().hex[:8]}"

    # Сохраняем транзакцию со статусом pending
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
            capture=False,  # двухстадийная оплата (холдирование)
        )
        # Обновляем provider_transaction_id
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
    """Подтверждает платеж (списывает холдированную сумму)."""
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
        # Обновляем статус
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
    """Отменяет платеж (если он в статусе waiting_for_capture)."""
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


async def get_payment_status(order_id: str, user_id: int) -> Dict[str, Any]:
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
    """Обработчик вебхука от ЮKassa."""
    return await payment_provider.handle_webhook(payload)


async def create_refund(
    order_id: str,
    user_id: int,
    amount: float,
    description: str = "Возврат средств",
) -> Dict[str, Any]:
    """Создает возврат по платежу."""
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
        # Можно сохранить refund_id в отдельную таблицу, но пока просто логируем
        logger.info(f"Refund created for payment {payment_id}: {result}")
        return result
    except Exception as e:
        logger.error(f"Refund creation failed: {e}", exc_info=True)
        raise HTTPException(500, f"Refund failed: {str(e)}")