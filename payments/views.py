import json
import time
from contextlib import suppress
from datetime import datetime

import stripe
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from loguru import logger
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet
from stripe import SignatureVerificationError

from bitapi.analysis.models import TextAnalysis, ScanData
from bitapi.payments.auto_pay import AutoPayService
from bitapi.payments.helpers import sub2plan, grant_credits, get_user_sub_db, get_price, is_more_expensive, \
    PRICE_NAME_MAP, get_current_sub
from bitapi.payments.models import StripePayment, StripeSubscription
from bitapi.utils import send_telegram_notification
from bitapi.utils import log_event, is_email, date_from_ts, now, create_or_update, success_response, \
    get_limits
from config.configuration import VIEW_DECORATOR, STRIPE_WEBHOOK_SECRET, FUNC_LOGGER, \
    ADMIN_SECRET, STRIPE_API_KEY, FRONT_URL
from config.settings.base import PAY_AS_YOU_GO
from bitapi.errors import ErrorTypes, Errors
from bitapi.users.models import User

stripe.api_key = STRIPE_API_KEY


# TODO: now auto-pay updating in text request.
# @receiver(post_save, sender=ScanData)
# @FUNC_LOGGER
# def user_updated(sender, instance, created, **kwargs):
#     try:
#         if created:
#             logger.info("ScanData created, fire AutoPay check {}", instance.id)
#             AutoPayService.update(User.objects.get(id=instance.user_id))
#     except Exception:
#         logger.exception("Failed to check AutoPay {}", instance.id)


def wait_for_subscription_update(subscription_id: str, last_date_updated: datetime | None, seconds=5):
    logger.info("Waiting for subscription update for")
    for i in range(seconds):
        try:
            subscription = StripeSubscription.objects.get(id=subscription_id)
            if subscription.date_updated != last_date_updated:
                return subscription
        except StripeSubscription.DoesNotExist:
            pass
        time.sleep(1)
    logger.error("Subscription update timeout")
    return None


@VIEW_DECORATOR
class CreateCheckoutSession(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_customer(self) -> str:
        if self.request.user.customer_id:
            return self.request.user.customer_id
        params = {}
        if self.request.user.email:
            params['email'] = self.request.user.email
        if self.request.user.name:
            params['name'] = self.request.user.name
        username = self.request.user.username
        if is_email(username):
            params['email'] = username
        customer = stripe.Customer.create(**params)

        self.request.user.customer_id = customer.id
        self.request.user.save()
        return customer.id

    def create_session(self, mode: str, price: str, metadata=None, url_param=None, **kwargs) -> stripe.checkout.Session:
        session = stripe.checkout.Session.create(
            line_items=[
                {
                    'price': price,
                    'quantity': 1,
                },
            ],
            allow_promotion_codes=True,
            customer=self.get_customer(),
            mode=mode,
            success_url=f'{FRONT_URL}/main/subscription?stripe=true&success=true&payment_type={url_param}&session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=f'{FRONT_URL}/main/subscription?stripe=true&canceled=true&payment_type={url_param}',
            metadata=metadata,
            **kwargs
        )
        return session

    @classmethod
    def get_price(cls, key: str) -> str:
        prices = stripe.Price.list(
            lookup_keys=[key],
        )
        return prices.data[0].id

    def create_new_subscription(self, price_name) -> stripe.checkout.Session:
        logger.info("Creating new subscription for user {} with price: {}", self.request.user.id, price_name)
        meta = {"type": price_name}
        return self.create_session(
            "subscription", self.get_price(price_name),
            metadata=meta,
            url_param="subscription"
        )

    def count_charges(self):
        return StripePayment.objects.filter(user=self.request.user, type="charge",
                                            status__in=["failed", "succeeded"]).count()

    @classmethod
    def wait_for_invoice(cls, invoice_id, seconds=5):
        for i in range(seconds):
            invoice = StripePayment.objects.filter(id=invoice_id).first()
            if invoice:
                return invoice
            time.sleep(1)

    def calculate_remaining_credit(self, sub: stripe.Subscription):

        # 2. Берём текущий тариф (предполагается один item)
        item = sub["items"]["data"][0]
        unit_amount = item["price"]["unit_amount"]  # сумма за период, в центах
        period_start = item["current_period_start"]  # UNIX
        period_end = item["current_period_end"]  # UNIX
        now = int(time.time())

        # 3. Считаем оставшуюся долю периода
        elapsed = max(now - period_start, 0)
        total = period_end - period_start
        remaining = max(total - elapsed, 0)

        # 4. Кредит = цена * (неиспользованные секунды / всего секунд)
        credit_cents = int(unit_amount * remaining / total)
        return credit_cents

    def change_plan_with_manual_credit(self, subscription_id: str, new_price_id: str):
        logger.info("Manual balance charge for subscription {} with price: {}", subscription_id, new_price_id)
        sub = stripe.Subscription.retrieve(
            subscription_id,
            expand=["items.data.price", "customer"]
        )
        credit_cents = self.calculate_remaining_credit(sub)
        cust = sub["customer"].id
        item = sub["items"]["data"][0]

        if credit_cents > 0:
            logger.info("Adding {} cents to customer balance", credit_cents)
            customer_obj = stripe.Customer.retrieve(cust)
            # TODO: take new plan price into account
            stripe.Customer.modify(
                cust,
                balance=customer_obj["balance"] - credit_cents
            )

        return stripe.Subscription.modify(
            subscription_id,
            items=[{
                "id": item["id"],
                "price": new_price_id
            }],
            proration_behavior="none",
            cancel_at_period_end=False,
            collection_method="charge_automatically"
        )

    @classmethod
    def handle_invoice(cls, invoice: stripe.Invoice | None) -> dict:
        response = {}
        if not invoice:
            raise Errors.server_error(ErrorTypes.failed_to_retrieve_invoice)

        response["id"] = invoice.id

        if invoice.status == "paid":
            response["invoice_status"] = "paid"

        elif invoice.status == "open":
            charge = stripe.Charge.retrieve(invoice.data["charge"])
            response["url"] = invoice.data["hosted_invoice_url"]
            response["type"] = "failed"
            response["failure_message"] = charge.failure_message
        else:
            raise Errors.server_error(ErrorTypes.unknown_invoice_status)
        return response

    def post(self, request, *args, **kwargs):
        plan = request.data.get("type")
        period = request.data.get("period")
        current_plan = sub2plan(self.request.user.subscription)
        price_name = f"{plan}-{period}"

        self.get_customer()  # create customer
        grant_credits(self.request.user)

        logger.info("Processing checkout session for user {} with subscription: {} (prev: {})",
                    self.request.user.id, plan, current_plan)

        subscription: StripeSubscription | None = get_user_sub_db(self.request.user)

        current_period = None
        if subscription:
            current_period = subscription.price.split("-")[1]

        response = {
            "url": None, "id": None, "type": None,
            "plan": plan, "period": period, "prev_plan": current_plan,
            "prev_period": current_period}

        if plan == "pay_as_you_go":
            session = self.create_session(
                "payment", self.get_price(plan),
                metadata={"type": "pay_as_you_go"},
                payment_intent_data={"metadata": {"type": "pay_as_you_go"}},
                url_param="pay_as_you_go"
            )
            response["url"] = session.url
            response["id"] = session.id
            response["type"] = "new"

        elif plan == "free":
            logger.info(f"Canceling subscriptions for user {self.request.user.id}")
            if not subscription:
                raise Errors.not_found(ErrorTypes.no_subscription_found)

            stripe.Subscription.modify(
                subscription.id,
                cancel_at_period_end=True
            )
            logger.info(f"Cancelled subscription {subscription.id}")
            response["type"] = "changed"
            response["change_type"] = "cancelled"
            response["id"] = subscription.id

        elif not subscription:
            session = self.create_new_subscription(price_name)
            response["url"] = session.url
            response["id"] = session.id
            response["type"] = "new"

        elif plan == current_plan and current_period == period:
            if price_name == get_price(subscription.data):
                raise Errors.not_acceptable(ErrorTypes.already_subscribed)

            new_price_id = self.get_price(price_name)
            logger.info(f"User {self.request.user.id} already subscribed to {plan} ({period}). Reverting")
            stripe.Subscription.modify(
                subscription.id,
                items=[{
                    "id": subscription.data["items"]["data"][-1]["id"],
                    "price": new_price_id,
                }],
                proration_behavior="none",
                collection_method="charge_automatically",
                cancel_at_period_end=False,
            )
            response["type"] = "reverted"

        elif plan in ["pro", "premium", "enterprise"]:

            if is_more_expensive(plan, current_plan) or (period == "yearly" and current_period == "monthly"):
                logger.info(f"Upgrading subscription for user {self.request.user.id} from {current_plan} to {plan}")
                change_type = "upgraded"
                # https://docs.stripe.com/billing/subscriptions/prorations
                proration_behavior = "always_invoice"

            else:
                logger.info(f"Downgrading subscription for user {self.request.user.id} from {current_plan} to {plan}")
                change_type = "downgraded"
                proration_behavior = "none"

            response["change_type"] = change_type
            new_price_id = self.get_price(price_name)

            if request.data.get("preview"):
                invoice = stripe.Invoice.create_preview(
                    customer=self.request.user.customer_id,
                    subscription=subscription.id,
                    subscription_details={
                        "proration_behavior": proration_behavior,
                        "items": [{
                            "id": subscription.data["items"]["data"][-1]["id"],
                            "deleted": True
                        }, {
                            "price": new_price_id
                        }],
                    }
                )
                response["invoice"] = dict(invoice)
                response["amount_due"] = invoice.amount_due
                response["type"] = "preview"
                if change_type == "downgraded":
                    response["amount_due"] = 0

            else:
                if period == "monthly" and current_period == "yearly":
                    # год -> месяц. Вернуть деньги, обновить подписку
                    stripe_subscription = self.change_plan_with_manual_credit(subscription.id, new_price_id)
                    response["change_type"] = "yearly_to_monthly"
                else:
                    # поменять stripe подписку,
                    # TODO если выбрана меньшая, но сейчас идет большая proration считается неправильно
                    #  при переходе еще выше (например на год с месяца)
                    stripe_subscription = stripe.Subscription.modify(
                        subscription.id,
                        items=[{
                            "id": subscription.data["items"]["data"][-1]["id"],
                            "price": new_price_id,
                        }],
                        proration_behavior=proration_behavior,
                        collection_method="charge_automatically",
                        cancel_at_period_end=False,
                    )

                wait_for_subscription_update(subscription.id, subscription.date_updated, seconds=15)

                if change_type == "upgraded":
                    invoice = self.wait_for_invoice(stripe_subscription.latest_invoice, seconds=15)

                    invoice_data = self.handle_invoice(invoice)
                    if invoice_data["invoice_status"] == "paid":
                        response["type"] = "changed"

                    response.update(invoice_data)

                else:
                    response["type"] = "changed"
                    # wait for subscription to update

        else:
            raise Errors.validation(f"Unknown subscription type: {plan}")

        return success_response(response)


@VIEW_DECORATOR
class StripeWebhook(APIView):
    """
    Local webhook accept:
    stripe listen --forward-to localhost:8000/api/payments/webhook

    SETUP at https://dashboard.stripe.com/webhooks
    Add events:
    invoice.paid invoice.updated
    charge.failed charge.succeeded charge.updated
    checkout.session.completed
    customer.subscription.created customer.subscription.updated
    customer.subscription.paused customer.subscription.resumed customer.subscription.deleted
    payment_intent.succeeded payment_intent.canceled
    """

    @classmethod
    def get_user_by_customer(cls, customer_id: str):
        try:
            return User.objects.get(customer_id=customer_id)
        except User.DoesNotExist:
            logger.error("Unknown customer_id: {}", customer_id)
            raise Errors.not_found("Unknown user (customer_id)")

    @classmethod
    def need_update_limits(cls, current_price: str | None, next_price: str):
        if not current_price:
            return True
        current_plan, current_period = current_price.split("-")
        next_plan, next_period = next_price.split("-")

        if current_period != next_period:
            return True
        if is_more_expensive(next_plan, current_plan):
            return True

        return False

    @classmethod
    def notify_change_subscription(cls, user: User, previous_subscription: str, subscription: str):
        logger.debug("Notifying subscription change for user {} from {} to {}",
                     user.id, previous_subscription, subscription)
        from bitapi.users.tasks import send_subscription_email_task
        from bitapi.users.models import find_user_utms
        from rest_framework.authtoken.models import Token
        from bitapi.utils import send_telegram_notification
        if subscription == previous_subscription:
            return

        if subscription != "Free":
            send_subscription_email_task.delay(
                email=user.email or user.username,
                name=user.name or user.username,
                subscription=subscription,
                token=Token.objects.get(user=user).key
            )
        message = (f"Subscription change:\n"
                   f"Name: {user.name}\n"
                   f"Email: {user.username}\n"
                   f"Id: {user.id}\n"
                   f"Subscription: {subscription}\n"
                   f"Prev: {previous_subscription}\n"
                   f"All utms: {' '.join(find_user_utms(user))}\n")

        send_telegram_notification(message)

    @classmethod
    def update_subscription(cls, user: User, data: dict):
        current_sub = get_user_sub_db(user)
        params = {
        }
        curr_price = None
        if current_sub:
            curr_price = current_sub.price
            if current_sub.id != data["id"]:
                logger.info("Event for different subscription, ignoring")
                return

        subscription_item = data["items"]["data"][-1]
        next_price = subscription_item["price"]["lookup_key"]

        logger.info("Updating subscription for user {} with status: {}", user.id, data["status"])

        if data["status"] == "active":
            if user.subscription == "Free":
                logger.info("User {} subscribed for the first time", user.id)
                user.subscription_start_date = now()
            # Split plan-period to get plan
            new_subscription = PRICE_NAME_MAP[next_price.split("-")[0]]
            user.premium_or_custom_available_until = date_from_ts(subscription_item["current_period_end"])
            user.save(update_fields=["subscription_start_date", "premium_or_custom_available_until"])

            prev_subscription = user.subscription
            if cls.need_update_limits(curr_price, next_price):
                user.subscription = new_subscription
                logger.debug("Set user.subscription to {}", new_subscription)
                cls.notify_change_subscription(user, prev_subscription, new_subscription)
                user.save(update_fields=["subscription"])

            params["price"] = next_price
            user.update_usage()
            # update price in subscription model

        if data["status"] == "canceled":
            logger.info("Subscription canceled for user {}", user.id)
            cls.notify_change_subscription(user, user.subscription, "Free")
            # Here was subscription deleting from db

        create_or_update(
            StripeSubscription,
            id=data["id"],
            status=data["status"],
            canceled=data["canceled_at"] is not None,
            current_period_end=date_from_ts(subscription_item["current_period_end"]),
            current_period_start=date_from_ts(subscription_item["current_period_start"]),
            data=data,
            user=user,
            **params
        )

    @classmethod
    def pay_as_you_go_paid(cls, user: User, data: dict):
        current_additional_limits = user.additional_limits or {}
        additional_limits = {}
        sum_limits = [
            "granted_words_simple_scan",
            "granted_british_words"
        ]
        for name in sum_limits:
            additional_limits[name] = current_additional_limits.get(name, 0) + PAY_AS_YOU_GO[name]

        user.additional_limits = additional_limits
        user.save()
        logger.info("User {} paid for Pay as you go", user.id)

    def post(self, request: Request, *args, **kwargs):
        # https://dashboard.stripe.com/webhooks
        raw_data = request.body
        try:
            signature = request.headers.get('stripe-signature')
            event = stripe.Webhook.construct_event(
                payload=raw_data, sig_header=signature, secret=STRIPE_WEBHOOK_SECRET)
        except SignatureVerificationError:
            raise Errors.not_acceptable(ErrorTypes.invalid_signature)
        data = event['data']["object"]
        event_type = event['type']
        user = None

        # Subscription events: https://docs.stripe.com/billing/subscriptions/webhooks
        logger.bind(event_type=event_type, data=json.dumps(data)).info("Stipe event: {}", event_type)
        # Debug output
        print(event_type)
        # print("-" + json.dumps(event))

        # It is important, allowing this event break the logic
        skip_events = [
            "payment_intent.created",
            "invoice.payment_succeeded",
            "invoice.created",
            "invoice.finalized"
        ]
        if event_type in skip_events:
            return success_response({'status': 'success'})

        if isinstance(data.get('customer'), str):
            user = self.get_user_by_customer(data["customer"])
            log_event("stripe__" + event_type, user=user)

        if event_type.startswith("customer.subscription."):
            self.update_subscription(user, data)

        if event_type == "invoice.payment_failed":
            # TODO: Make some processing
            logger.error("Payment failed for invoice: {} user_id: {} ({})", data["id"], user.id, user.username)

        if event_type == "checkout.session.completed" and data["metadata"].get("type") == "pay_as_you_go":
            self.pay_as_you_go_paid(user, data)

        if event_type == "charge.succeeded":
            with suppress(Exception):
                send_telegram_notification(
                    f"New charge:\n"
                    f"Username: {user.username}\n"
                    f"Amount: ${data['amount'] / 100}\n"
                )

        if (event_type.startswith("payment_intent.") or
              event_type.startswith("invoice.") or
              event_type.startswith("charge.")):
            create_or_update(
                StripePayment,
                id=data["id"],
                type=event_type.split(".")[0],
                status=data["status"],
                data=data,
                user=user
            )

        return success_response({'status': 'success'})


class CustomerPortal(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        if not self.request.user.customer_id:
            raise Errors.not_found("Customer not found")

        portal_session = stripe.billing_portal.Session.create(
            customer=self.request.user.customer_id,
            return_url=f"{FRONT_URL}/main/subscription",
        )
        log_event("payments__customer_portal", user=self.request.user)
        return success_response({
            "url": portal_session.url
        })


class GetPaymentsDetails(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @classmethod
    def get_payment_method(cls, method):
        type_ = method.get("type")
        res = {
            "type": type_,
        }
        options = method.get(type_, {})
        if type_ == "card":
            res["key"] = options.get("last4")
            res["brand"] = options.get("display_brand")
            res["card"] = options.get("last4")
        elif type_ == "link":
            res["key"] = options.get("email")
            res["brand"] = "link"
        else:
            logger.error("Unknown payment method type: {}", type_)
            return {}
        return res

    def payment_methods(self):
        customer_id = self.request.user.customer_id
        if not customer_id:
            return []
        try:
            customer = stripe.Customer.retrieve(customer_id)
            pm_id = customer.get("invoice_settings", {}).get("default_payment_method")
            methods = {}
            payment_methods = stripe.PaymentMethod.list(customer=customer_id)
            for method in payment_methods:
                pm = self.get_payment_method(method)

                if pm:
                    pm["id"] = method["id"]
                    pm["default"] = pm["id"] == pm_id
                    if pm["key"] not in methods or pm["default"]:
                        methods[pm["key"]] = pm
            items = list(methods.values())
            if items and not any([item.get("default") for item in items]):
                items[0]["default"] = True
            return items
        except Exception as e:
            logger.exception("Error getting payment methods")
            return []

    def payments(self):
        payment_items = []
        try:
            payments = StripePayment.objects.filter(user=self.request.user).order_by("-date_created")
            for p in payments:
                data = p.data
                payment_item = {}
                charge = None

                if p.type == "payment_intent" and data["metadata"].get("type") in ["pay_as_you_go", "auto_pay"]:
                    charge = (
                        StripePayment.objects.filter(user=self.request.user, type="charge",
                                                     data__payment_intent=data["id"])
                        .order_by("-date_created").first())
                    payment_item = {
                        "id": p.id,
                        "type": data["metadata"].get("type"),
                        "date": p.date_created,
                        "amount": round(data["amount"] / 100, 2),
                    }
                elif p.type == "invoice":
                    if not data["paid"]:
                        logger.debug("Invoice not paid")
                        continue
                    charge = StripePayment.objects.filter(id=data["charge"]).first()
                    payment_item = {
                        "type": data["lines"]["data"][-1]["price"]["lookup_key"].split("-")[0],
                        "id": p.id,
                        "url": data["invoice_pdf"],
                        "date": p.date_created,
                        "amount": round(data["amount_paid"] / 100, 2),
                    }

                if charge:
                    payment_item["url"] = charge.data["receipt_url"]
                    payment_item["payment_method"] = self.get_payment_method(charge.data["payment_method_details"])

                if payment_item:
                    # if not payment_item["amount"]:
                    #     logger.debug("Payment amount not found {}", payment_item["id"])
                    #     continue
                    payment_items.append(payment_item)
        except Exception as e:
            logger.exception("Error getting payments")
        return payment_items

    def subscription(self):
        try:
            subscription = get_user_sub_db(self.request.user)
            sub = get_current_sub(self.request.user)
            if sub:
                return {
                    "id": sub["id"],
                    "cancel_at_period_end": sub["cancel_at_period_end"],
                    "auto_pay": subscription.auto_pay,
                }
        except Exception as e:
            logger.exception("Error getting subscription")
        return {}

    def get(self, request, *args, **kwargs):

        return success_response({
            "methods": self.payment_methods(),
            "payments": self.payments(),
            "subscription": self.subscription()
        })

    def post(self, request, *args, **kwargs):
        if request.data.get("default_payment_method"):
            logger.info("Updating default payment method for user {}", self.request.user.id)
            customer = stripe.Customer.retrieve(self.request.user.customer_id)
            customer.invoice_settings.default_payment_method = request.data["default_payment_method"]
            customer.save()
        else:
            logger.error("No data to change")
        return self.get(request, *args, **kwargs)


class SetupAutoPay(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        if not self.request.user.customer_id:
            raise Errors.not_found("Customer not found")
        subscription = get_user_sub_db(self.request.user)
        if not subscription:
            raise Errors.not_found("Subscription not found")

        enabled = request.data["enabled"]
        limit = request.data["limit"]
        add = request.data.get("add_amount")

        if limit < 10000 or limit > 500000:
            raise Errors.not_acceptable("Limit must be between 10000 and 500000")
        if add and (add < 50000 or add > 10000000):
            raise Errors.not_acceptable("Add must be between 50000 and 10000000")

        subscription.auto_pay = {
            "enabled": enabled,
            "limit": limit,
            "add_amount": add
        }
        subscription.save()
        return success_response(subscription.auto_pay)


class WaitCheckoutComplete(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @classmethod
    def wait_for_session(cls, session_id: str):
        session = stripe.checkout.Session.retrieve(session_id)
        wait_for_subscription_update(session.subscription, None, seconds=10)

    def post(self, request, *args, **kwargs):
        if request.data.get("session_id"):
            self.wait_for_session(request.data.get("session_id"))
        return success_response({})

class HasAdminSecret(BasePermission):
    def has_permission(self, request, view):
        return request.data.get("secret") == ADMIN_SECRET

class PaymentsUtils(ViewSet):
    permission_classes = [HasAdminSecret]
    authentication_classes = []

    def gen_promo_codes(self, request: Request):
        data = request.data
        coupon_id = data.get("coupon_id")
        count = data.get("count", 1)
        max_redemptions = data.get("max_redemptions", 1)
        restrictions = data.get("restrictions", {})
        logger.info("Generating promo codes: {} for coupon {}", count, coupon_id)

        codes: list[stripe.PromotionCode] = []
        for i in range(count):
            codes.append(
                stripe.PromotionCode.create(coupon=coupon_id, max_redemptions=max_redemptions, restrictions=restrictions)
            )
        return success_response({
            "codes": [c.code for c in codes],
        })
