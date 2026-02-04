from django.apps import AppConfig


class YookassaPaymentsConfig(AppConfig):
    name = "yookassa_payments"

    def ready(self):
        # from yookassa_payments.tasks import withdraw_money
        #
        # withdraw_money(
        #     **{
        #         "amount": 100.0,
        #         "metadata": {
        #             "auto_pay": False,
        #             "product": "pro_month_subscription",
        #             "trial": False,
        #             "user_id": 4,
        #         },
        #         "payment_method_id": "3115a831-0037-5000-8000-0d92f345c39e",
        #     }
        # )
        pass
