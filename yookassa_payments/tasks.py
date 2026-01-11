from celery import shared_task
from yookassa import Payment
from core.models import Product


@shared_task
def withdraw_money_for_product(payment_method_id, product_id):
    product = Product.objects.get(pk=product_id)
    payment = Payment.create(
        {
            "amount": {"value": product.month_price, "currency": "RUB"},
            "capture": True,
            "payment_method_id": payment_method_id,
            "description": "Заказ",
        }
    )
    return payment.json()
