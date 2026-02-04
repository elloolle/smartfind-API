from copy import deepcopy

from django.conf import settings


def payment_succeeded(user_id, product_name="pro_month_subscription"):
    return {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {
            "id": "30f5d918-000f-5001-9000-14efbe8f8527",
            "status": "succeeded",
            "amount": {"value": "100.00", "currency": "RUB"},
            "income_amount": {"value": "95.73", "currency": "RUB"},
            "recipient": {"account_id": "1239880", "gateway_id": "2617846"},
            "payment_method": {
                "type": "yoo_money",
                "id": "30f5d918-000f-5001-9000-14efbe8f8527",
                "saved": True,
                "status": "active",
                "title": "YooMoney wallet 410011758831136",
                "account_number": "410011758831136",
            },
            "captured_at": "2026-01-11T15:44:35.557Z",
            "created_at": "2026-01-11T15:44:24.482Z",
            "test": True,
            "refunded_amount": {"value": "0.00", "currency": "RUB"},
            "paid": True,
            "refundable": True,
            "metadata": {
                "user_id": str(user_id),
                "cms_name": "yookassa_sdk_python",
                "product": product_name,
            },
        },
    }


def trial_payment_succeeded(user_id):
    payload = payment_succeeded(user_id, settings.TRIAL_PRODUCT_NAME)
    payload["object"]["metadata"]["trial"] = True
    return payload


def payment_canceled_bank_card(user_id, auto_pay=False, trial=False):
    return {
        "type": "notification",
        "event": "payment.canceled",
        "object": {
            "id": "3115b117-000f-5000-8000-1f9301667ef8",
            "status": "canceled",
            "amount": {"value": "100.00", "currency": "RUB"},
            "description": "Р—Р°РєР°Р·",
            "recipient": {"account_id": "1239880", "gateway_id": "2617846"},
            "payment_method": {
                "type": "bank_card",
                "id": "3115a831-0037-5000-8000-0d92f345c39e",
                "saved": True,
                "status": "active",
                "title": "Bank card *0079",
                "card": {
                    "first6": "220000",
                    "last4": "0079",
                    "expiry_year": "2030",
                    "expiry_month": "11",
                    "card_type": "Mir",
                },
            },
            "created_at": "2026-02-04T19:26:15.814Z",
            "test": True,
            "paid": False,
            "refundable": False,
            "metadata": {
                "product": "pro_month_subscription",
                "user_id": str(user_id),
                "auto_pay": auto_pay,
                "cms_name": "yookassa_sdk_python",
                "trial": trial,
            },
            "cancellation_details": {
                "party": "payment_network",
                "reason": "insufficient_funds",
            },
            "authorization_details": {
                "rrn": "774669329399449",
                "auth_code": "659121",
                "three_d_secure": {
                    "applied": False,
                    "method_completed": False,
                    "challenge_completed": False,
                },
            },
        },
    }


def payment_method_active_bank_card(payment_method_id):
    return {
        "type": "notification",
        "event": "payment_method.active",
        "object": {
            "type": "bank_card",
            "id": payment_method_id,
            "saved": True,
            "status": "active",
            "holder": {"account_id": "1239880", "gateway_id": "2617846"},
            "title": "Bank card *2987",
            "card": {
                "first6": "220247",
                "last4": "2987",
                "expiry_year": "2030",
                "expiry_month": "11",
                "card_type": "Mir",
            },
        },
    }


def payment_succeeded_bank_card(user_id, payment_method_id="card_method"):
    payload = payment_succeeded(user_id)
    payload["object"]["payment_method"] = {
        "type": "bank_card",
        "id": payment_method_id,
        "card": {
            "first6": "411111",
            "last4": "1111",
            "expiry_year": "2028",
            "expiry_month": "09",
        },
    }
    return payload


def copy_payload(payload):
    return deepcopy(payload)
