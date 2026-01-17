from celery import shared_task
from yookassa import Payment


@shared_task
def withdraw_money(payment_method_id, amount, metadata):
    payment = Payment.create(
        {
            "amount": {"value": amount, "currency": "RUB"},
            "capture": True,
            "payment_method_id": payment_method_id,
            "description": "Заказ",
            "metadata": metadata,
        }
    )
    return payment.json()
