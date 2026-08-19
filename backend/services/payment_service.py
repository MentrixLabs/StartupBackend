# backend/services/payment_service.py
import logging
import uuid
from typing import Optional, Dict, Any
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from db.db import async_session_maker
from db.ozon.dao import PaymentTransactionDAO
from config import settings

logger = logging.getLogger(__name__)

# Импортируем клиент ЮKassa (установите: pip install yookassa)
# from yookassa import Configuration, Payment

class BasePaymentProvider:
    """Абстрактный класс для платёжного провайдера."""
    async def create_payment(self, amount: float, description: str, order_id: str, user_id: int) -> Dict[str, Any]:
        raise NotImplementedError

    async def handle_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

class YooKassaProvider(BasePaymentProvider):
    """Реализация для ЮKassa."""
    def __init__(self):
        # Настройка клиента
        # Configuration.account_id = settings.YOOKASSA_SHOP_ID
        # Configuration.secret_key = settings.YOOKASSA_SECRET_KEY
        pass

    async def create_payment(self, amount: float, description: str, order_id: str, user_id: int) -> Dict[str, Any]:
        """
        Создаёт платёж в ЮKassa и возвращает URL для оплаты.
        """
        # В реальности здесь будет вызов API ЮKassa
        # Пример:
        # payment = Payment.create({
        #     "amount": {"value": f"{amount:.2f}", "currency": "RUB"},
        #     "confirmation": {"type": "redirect", "return_url": "https://your-frontend/payment-success"},
        #     "capture": True,
        #     "description": description,
        #     "metadata": {"order_id": order_id, "user_id": user_id}
        # })
        # return {
        #     "payment_id": payment.id,
        #     "confirmation_url": payment.confirmation.confirmation_url,
        #     "status": payment.status
        # }

        # Заглушка для теста (имитация)
        logger.info(f"Создан платёж {order_id} на сумму {amount} RUB для пользователя {user_id}")
        return {
            "payment_id": f"test_{uuid.uuid4().hex[:8]}",
            "confirmation_url": f"https://test-payment.com/pay/{order_id}",
            "status": "pending"
        }

    async def handle_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обрабатывает вебхук от ЮKassa.
        Ожидает, что в payload есть event и объект платежа.
        """
        event = payload.get("event")
        if event is None:
            raise HTTPException(400, "Missing event field")

        payment_data = payload.get("object")
        if not payment_data:
            raise HTTPException(400, "Missing payment object")

        # Извлекаем метаданные
        metadata = payment_data.get("metadata", {})
        order_id = metadata.get("order_id")
        if not order_id:
            logger.error("order_id not found in metadata")
            return {"status": "error", "message": "order_id missing"}

        provider_transaction_id = payment_data.get("id")
        status = payment_data.get("status")  # "succeeded", "canceled"

        async with async_session_maker() as session:
            # Находим транзакцию
            transaction = await PaymentTransactionDAO.find_one_or_none(order_id=order_id)
            if not transaction:
                logger.warning(f"Transaction for order {order_id} not found")
                return {"status": "error", "message": "transaction not found"}

            # Обновляем статус
            new_status = "succeeded" if status == "succeeded" else "canceled" if status == "canceled" else "pending"
            if new_status != transaction.status:
                await PaymentTransactionDAO.update(
                    order_id=order_id,
                    status=new_status,
                    provider_transaction_id=provider_transaction_id,
                    updated_at=datetime.utcnow()
                )
                logger.info(f"Transaction {order_id} updated to {new_status}")

        return {"status": "ok"}

# Создаём экземпляр провайдера (можно выбрать в зависимости от конфига)
payment_provider = YooKassaProvider()

# --- Публичные функции сервиса ---

async def create_payment(user_id: int, amount: float, description: str = "Оплата услуги") -> Dict[str, Any]:
    """
    Создаёт платёж для пользователя.
    """
    order_id = f"ORDER-{user_id}-{uuid.uuid4().hex[:8]}"

    # Сохраняем транзакцию со статусом pending
    async with async_session_maker() as session:
        await PaymentTransactionDAO.add(
            user_id=user_id,
            order_id=order_id,
            amount=amount,
            status="pending",
            description=description
        )

    # Запрашиваем у провайдера
    try:
        result = await payment_provider.create_payment(amount, description, order_id, user_id)
        # Обновляем provider_transaction_id
        async with async_session_maker() as session:
            await PaymentTransactionDAO.update(
                order_id=order_id,
                provider_transaction_id=result.get("payment_id")
            )
        return {
            "order_id": order_id,
            "payment_id": result.get("payment_id"),
            "confirmation_url": result.get("confirmation_url"),
            "status": result.get("status")
        }
    except Exception as e:
        logger.error(f"Payment creation failed: {e}")
        # Можно пометить транзакцию как failed
        async with async_session_maker() as session:
            await PaymentTransactionDAO.update(order_id=order_id, status="failed")
        raise HTTPException(500, "Payment creation failed")

async def handle_webhook(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Обработчик вебхука от платёжной системы.
    """
    return await payment_provider.handle_webhook(payload)

async def get_transaction_status(order_id: str, user_id: int) -> Dict[str, Any]:
    """
    Получить статус транзакции по её order_id для конкретного пользователя.
    """
    async with async_session_maker() as session:
        transaction = await PaymentTransactionDAO.find_one_or_none(order_id=order_id, user_id=user_id)
        if not transaction:
            raise HTTPException(404, "Transaction not found")
        return {
            "order_id": transaction.order_id,
            "status": transaction.status,
            "amount": transaction.amount,
            "created_at": transaction.created_at.isoformat(),
            "description": transaction.description
        }