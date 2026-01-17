from django.conf import settings
from loguru import logger


def make_anonymous_card(first6, last4):
    return first6[0:4] + " " + first6[4:6] + 2 * "*" + " " + 4 * "*" + " " + last4
