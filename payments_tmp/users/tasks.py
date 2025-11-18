from django.core import mail
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

from bitapi.utils import is_email
from config import celery_app
from config.configuration import FUNC_LOGGER
from loguru import logger


def send_user_email(subject, html, recipient_email, from_email_type: str):
    if from_email_type == "noreply":
        from_email = f"It's AI <{settings.NOREPLY_EMAIL_HOST_USER}>"
        host = settings.NOREPLY_EMAIL_HOST
        password = settings.NOREPLY_EMAIL_HOST_PASSWORD
        username = settings.NOREPLY_EMAIL_HOST_USER

    elif from_email_type == "sales":
        from_email = f"It's AI <{settings.SALES_EMAIL_HOST_USER}>"
        host = settings.SALES_EMAIL_HOST
        password = settings.SALES_EMAIL_HOST_PASSWORD
        username = settings.SALES_EMAIL_HOST_USER
    else:

        raise ValueError("Unknown from_email: " + from_email_type)

    base_plain = strip_tags(html)
    with mail.get_connection(
        backend="bitapi.email_backends.SentImapEmailBackend",
        host=host,
        port=settings.EMAIL_PORT,
        username=username,
        use_tls=settings.EMAIL_USE_TLS,
        use_ssl=settings.EMAIL_USE_SSL,
        password=password,
    ) as connection:
        first_msg = EmailMultiAlternatives(
            subject=subject,
            body=base_plain,
            from_email=from_email,
            to=[recipient_email],
            connection=connection
        )
        first_msg.attach_alternative(html, "text/html")
        first_msg.send()


@celery_app.task()
@FUNC_LOGGER
def send_introduction_email_task(email, name, token=None):
    if not is_email(email):
        logger.warning("send_introduction_email_task: Not valid email, skip: {}", email)
        return
    recipient_email = email
    subject = "Welcome to It's AI!"
    html_content = render_to_string("introduction_email.html",
                                    {"email": email, "name": name or email, "token": token})

    send_user_email(subject, html_content, recipient_email, "noreply")


@celery_app.task()
@FUNC_LOGGER
def send_subscription_email_task(email, name, subscription, token=None):
    if not is_email(email):
        logger.warning("send_subscription_email_task: Not valid email, skip: {}", email)
        return
    logger.info("Will send subscription email {} {} {}", email, name, subscription)
    recipient_email = email
    subject = "Change subscription"
    html_content = render_to_string("email_subscription.html",
                                    {"email": email, "name": name or email,
                                     "token": token, "subscription": subscription})
    try:

        send_user_email(subject, html_content, recipient_email, "noreply")
    except TimeoutError as e:
        logger.error("send_subscription_email_task: TimeoutError: {}", e)
