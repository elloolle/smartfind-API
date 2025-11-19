import django
from django.conf import settings


def now():
    return django.utils.timezone.now()


def makeChoicesEnum(list):
    def wrap(cls):
        for item in list:
            setattr(cls, item, item)

        @classmethod
        def choices(cls):
            return [(member, member) for member in cls]

        setattr(cls, "choices", choices)
        return cls

    return wrap


def get_subscription_plan_from_product_name(product_name):
    product = settings.PRODUCTS[product_name]
    return product["plan"]
