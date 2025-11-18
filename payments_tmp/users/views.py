from contextlib import suppress
from datetime import timedelta

import jwt
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse
from django.views.generic import RedirectView, UpdateView, DetailView
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import action
from rest_framework.viewsets import ViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from django.db import IntegrityError
from django.utils.translation import gettext_lazy as lazy

from config.configuration import VIEW_DECORATOR, PRIVY_VERIFICATION_KEY, PRIVY_APP_ID
from .serializers import (
    SignUpSerializer,
    UserSerializer,
    QuestionnaireSerializer,
    SocialMediaSubscribeRequestSerializer
)

from rest_framework.generics import CreateAPIView
from rest_framework.views import APIView
from loguru import logger

from bitapi.analysis.models import TextAnalysis
from bitapi.payments.models import StripePayment, StripeSubscription

from mixpanel import Mixpanel
from django.conf import settings

from bitapi.users.models import SubscribeRequest, User, find_user_utms, UserOptions
from bitapi.users.tasks import send_introduction_email_task
from bitapi.utils import count_words_from_objects, now, success_response, log_event, send_telegram_notification, \
    put_not_none, create_or_update, is_type_or_none
from bitapi.errors import ErrorTypes, Errors
from ..payments.views import HasAdminSecret

User = get_user_model()


def save_mixpanel_event(user, event_name, properties=None):
    """
    Save a Mixpanel event for the given user.

    Args:
    user (User): The user object for which the event is being tracked.
    event_name (str): The name of the event to be tracked.
    properties (dict, optional): Additional properties for the event. Defaults to None.

    Returns:
    None
    """
    logger.debug(f"Attempting to save Mixpanel event '{event_name}' for user {user.id}")
    if not settings.MIXPANEL_TOKEN:
        logger.warning("No Mixpanel token configured, skipping event tracking")
        return

    mp = Mixpanel(settings.MIXPANEL_TOKEN)

    if properties is None:
        properties = {}

    properties['distinct_id'] = user.id
    properties['username'] = user.username

    mp.track(user.id, event_name, properties)
    logger.info(f"Successfully tracked Mixpanel event '{event_name}' for user {user.id}")


def set_user_options(user, **values):
    create_or_update(
        UserOptions,
        pk=user.id,
        **values
    )


class GetMeView(APIView):
    """
    Main endpoint for getting user details
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_open_invoice(self):
        user = self.request.user
        unpaid_subscription = StripeSubscription.objects.filter(user=user, status="past_due").last()
        if not unpaid_subscription:
            return None
        open_invoice = unpaid_subscription.data["latest_invoice"]
        invoice = StripePayment.objects.filter(id=open_invoice).first()
        if not invoice:
            logger.error("Invoice not found for unpaid_subscription: {}", open_invoice)
            return None
        charge = StripePayment.objects.filter(id=invoice.data["charge"]).first()
        if not charge:
            logger.error("Charge not found for invoice: {}", invoice.id)
            return None
        return {
            "hosted_invoice_url": invoice.data["hosted_invoice_url"],
            "invoice_id": invoice.id,
            "charge_id": charge.id,
            "description": charge.data["description"],
            "failure_code": charge.data["failure_code"],
            "failure_message": charge.data["failure_message"],
            "amount": charge.data["amount"],
            "paid": charge.data["paid"]
        }

    def get_subscription_payments(self):
        from bitapi.payments.views import get_user_sub_db
        user = self.request.user
        subscription = get_user_sub_db(user)
        if not subscription:
            return None
        next_price = subscription.data["items"]["data"][-1]["price"]["lookup_key"]
        return {
            "plan": next_price.split("-")[0],
            "period": next_price.split("-")[1]
        }

    def get_scan_count(self) -> int:
        return TextAnalysis.objects.filter(user=self.request.user).count()

    def update_user(self):
        user = self.request.user
        user.last_login = now()
        user.save(update_fields=["last_login"])
        user.update_usage()

    def get_user_options(self):
        options = UserOptions.objects.filter(user=self.request.user).first()
        if not options:
            return {}

        return {
            "feedback_provided": bool(options.feedback),
            "policy_accepted": options.policy_accepted,
            **(options.overrides or {})
        }

    def get(self, request):
        logger.debug(f"Getting user details for user {request.user.id}")
        self.update_user()
        serializer = UserSerializer(request.user, context={"request": request})

        response = serializer.data
        put_not_none(response, "open_invoice", self.get_open_invoice())
        put_not_none(response, "subscription_payments", self.get_subscription_payments())

        response["scan_count"] = self.get_scan_count()
        response.update(self.get_user_options())
        return success_response(response)


@VIEW_DECORATOR
class SignUpLoginView(APIView):
    serializer_class = SignUpSerializer
    permission_classes = []
    authentication_classes = []

    def signup(self, request, attempt=1):
        if attempt >= 3:
            raise Errors.limitation("Too many attempts of signup")
        # SIGNUP AND LOGIN
        logger.info("Processing auth request")

        privy_id = request.data.get("password")
        username = request.data.get("username")
        anon_username = request.data.get("anon_username")
        access_token = request.headers.get("Authorization")
        client_id = request.data.get("client_id")
        source = request.data.get("source", "Email")

        if not privy_id:
            raise Errors.validation(ErrorTypes.no_password)
        if not username:
            raise Errors.validation(ErrorTypes.no_password)
        if not client_id:
            logger.warning("No client_id provided on auth")

        anon_user = None
        if anon_username:
            with suppress(User.DoesNotExist):
                anon_user = User.objects.get(username=anon_username, is_anon=True)

        # LOGIN
        try:
            user = User.objects.get(username=username)
            if user.privy_id and user.privy_id != privy_id:
                raise Errors.authentication_failed(ErrorTypes.unknown_privy_user)
            if not user.check_password(privy_id) and not user.check_password(privy_id.split(":")[-1]):
                raise Errors.authentication_failed(ErrorTypes.wrong_password)

            if client_id:
                user.client_id = client_id
            if anon_user:
                user.registered_user = anon_user
                anon_user.registered_user = user
                anon_user.save()

            user.save()
            token, created = Token.objects.get_or_create(user=user)
            log_event("login", user=user)
            return success_response({"token": token.key})
        except User.DoesNotExist:
            pass

        if not access_token or not access_token.startswith("Bearer "):
            raise Errors.authentication_failed(ErrorTypes.no_access_token)
        else:
            try:
                access_token = access_token.replace("Bearer ", "")
                decoded = jwt.decode(access_token, PRIVY_VERIFICATION_KEY, issuer='privy.io', audience=PRIVY_APP_ID,
                                     algorithms=['ES256'])
                if decoded["sub"] != privy_id:
                    raise Errors.authentication_failed(ErrorTypes.invalid_password)
            except Exception as e:
                logger.exception("Failed to verify access token")
                raise Errors.authentication_failed(ErrorTypes.token_verification_failed)

        # SIGNUP
        logger.debug("Creating new user with username: {}", username)
        try:
            user = User.objects.create_user(
                username=username,
                password=privy_id,
                client_id=client_id,
                registration_type=source,
                registered_user=anon_user,
                # Without this users can create lots of accounts with different usernames and same password and access_token
                privy_id=privy_id
            )
            log_event("signup", user=user)
        except IntegrityError:
            logger.warning("Username already exists in create_user attempt (race)")
            return self.signup(request, attempt + 1)
        if anon_user:
            anon_user.registered_user = user
        token, created = Token.objects.get_or_create(user=user)
        logger.info(f"Successfully created user {user.id}")

        return success_response({"token": token.key})

    def post(self, request):
        return self.signup(request)


@VIEW_DECORATOR
class UserActionsViewSet(ViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['POST'])
    def feedback(self, request):
        user = self.request.user
        rating = self.request.data.get("rating")
        message = self.request.data.get("message")
        rejected = self.request.data.get("rejected")

        assert is_type_or_none(rating, int), "rating must be an integer"
        assert is_type_or_none(rejected, bool), "rejected must bool"
        assert is_type_or_none(message, str), "message must be a string"
        if message and len(message) > 1000:
            logger.error(f"Feedback message too long for user {user.id}, truncating")
            message = message[:1000]

        if rejected:
            feedback = {
                "rejected": True,
            }
        else:
            feedback = {
                "rating": rating,
                "message": message,
            }
        set_user_options(user=user, feedback=feedback)
        return success_response()

    @action(detail=False, methods=['POST'])
    def accept_policy(self, request):
        from bitapi.dynamic_config.apps import DB_CONFIG
        policy_version = DB_CONFIG.get("POLICY_VERSION")
        ip = request.META.get('REMOTE_ADDR')
        set_user_options(
            user=request.user,
            policy_accepted=True,
            policy_timestamp=now(),
            policy_ip=ip,
            policy_version=policy_version,
        )
        return success_response()

    @action(detail=False, methods=['POST'])
    def set_name_and_role(self, request):
        user = request.user
        user.name = request.data.get('name')
        user.role = request.data.get('role')
        user.save()

        logger.info(f"Sending introduction email to {user.username}")
        send_introduction_email_task.delay(
            email=user.username,
            name=user.name or user.username,
            token=Token.objects.get(user=user).key
        )

        return success_response()

    @action(detail=False, methods=["GET"])
    def usage(self, request):
        user = request.user
        week_ago = now() - timedelta(days=7)
        texts = (TextAnalysis.objects.filter(user=user, date_created__gt=week_ago)
                 .order_by("-date_created").all())
        words_count = count_words_from_objects(texts)
        return success_response({
            "weak_daily_avg": round(words_count / 7, 1)
        })

    @action(detail=False, methods=['GET'], permission_classes=[])
    def get_user_by_header(self, request):
        token = request.headers.get('Authorization').split(' ')[1]
        user = Token.objects.get(key=token).user
        serializer = UserSerializer(user, context={"request": request})
        return success_response(serializer.data)

    @action(detail=False, methods=['POST'])
    def track_event(self, request):
        logger.info(f"Processing event tracking for user {request.user.id}")
        user = request.user
        event_name = request.data.get('event_name')
        properties = request.data.get('properties', {})

        if not event_name:
            raise Errors.validation(ErrorTypes.event_name_required)

        save_mixpanel_event(user, event_name, properties)
        logger.info(f"Successfully tracked event '{event_name}' for user {user.id}")
        return success_response({'message': 'Event tracked successfully'})

    @action(detail=False, methods=['POST'])
    def complete_onboarding(self, request):
        user = request.user
        user.onboarding_completed = True
        user.save(update_fields=['onboarding_completed'])
        return success_response({'message': 'Onboarding completed successfully'})

    @action(detail=False, methods=['POST'])
    def enroll_user(self, request):
        user = request.user
        user.enrolled = True
        user.save(update_fields=['enrolled'])
        return success_response({'message': 'User enrolled successfully'})

    @action(detail=False, methods=['POST'])
    def map_anon_user(self, request):
        logger.info(f"Processing anon user mapping for user {request.user.id}")
        user = request.user
        anon_username = request.data.get('anon_username')
        logger.debug(f"Attempting to map anon user: {anon_username}")

        if not anon_username:
            logger.warning("Mapping failed - no anon username provided")
            raise Errors.validation(ErrorTypes.server, message="anon_username is required")

        try:
            anon_user = User.objects.get(username=anon_username, is_anon=True)

            user.registered_user = anon_user

            anon_user.registered_user = user
            anon_user.save()
            logger.info(f"Successfully mapped anon user {anon_username} to user {user.id}")

            return success_response({'message': 'Anon user mapped successfully'})

        except User.DoesNotExist:
            raise Errors.not_found("Anon user not found")

    @action(detail=False, methods=['POST'])
    def unsubscribe(self, request):
        user = request.user
        user.unsubscribed_emails = True
        user.save()
        logger.info(f"Unsubscribing user {request.user.id}")
        return success_response({'message': 'User unsubscribed successfully'})


@VIEW_DECORATOR
class CreateSubscribeRequest(APIView):
    model = SubscribeRequest
    queryset = SubscribeRequest.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @classmethod
    def send_telegram_notification(cls, user, entity):

        message = f"New SubscribeRequest created:\nName: {user.name}\nId: {user.id}\nIs free: {entity.is_free}\nall utms: {' '.join(find_user_utms(user))}\nemail: {user.username}\nsubscription name: {entity.role_name}"

        send_telegram_notification(message)

    @classmethod
    def notify(cls, entity):
        user = entity.user
        cls.send_telegram_notification(user, entity)

    @classmethod
    def grant_premium(cls, user):
        have_free_premium = SubscribeRequest.objects.filter(user=user, role_name='Premium').exists()
        if have_free_premium:
            raise Errors.validation(ErrorTypes.server, message="User were already granted free premium")
        logger.info(f"Granting premium to user {user.id}")
        user.subscription = "Premium"
        user.premium_or_custom_available_until = now() + timedelta(days=30)
        user.save(update_fields=['subscription', 'premium_or_custom_available_until'])

    def post(self, request, *args, **kwargs):
        user = request.user
        data = request.data
        name = data.pop('name')
        if name:
            user.name = name
            user.save(update_fields=['name'])

        if data.get("role_name") == "Premium" and data.get("is_free"):
            self.grant_premium(user)

        user.update_usage()
        entity = SubscribeRequest.objects.create(user=user, **data)

        self.notify(entity)

        return success_response({
            "id": entity.id,
            "is_free": entity.is_free,
            "role_name": entity.role_name,
        })


@VIEW_DECORATOR
class LoginView(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        client_id = request.data.get("client_id")

        if client_id:
            try:
                serializer = self.get_serializer(data=request.data)
                logger.debug(f"Serializer data: {serializer.initial_data}")
                serializer.is_valid(raise_exception=True)
                user = serializer.validated_data['user']
                user.client_id = client_id
                user.save()
            except Exception:
                logger.exception("Pre authorization updating failed {}".format(request.data))

        return super().post(request, *args, **kwargs)


@VIEW_DECORATOR
class CreateQuestionnaire(CreateAPIView):
    serializer_class = QuestionnaireSerializer
    permission_classes = [IsAuthenticated]


@VIEW_DECORATOR
class CreateSocialMediaSubscribeRequest(CreateAPIView):
    serializer_class = SocialMediaSubscribeRequestSerializer
    permission_classes = [IsAuthenticated]


@VIEW_DECORATOR
class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    slug_field = "username"
    slug_url_kwarg = "username"


@VIEW_DECORATOR
class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    fields = ["name"]
    success_message = lazy("Information successfully updated")

    def get_success_url(self):
        assert self.request.user.is_authenticated  # for mypy to know that the user is authenticated
        return self.request.user.get_absolute_url()

    def get_object(self):
        return self.request.user


@VIEW_DECORATOR
class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self):
        return reverse("users:detail", kwargs={"username": self.request.user.username})


class TestingUtil(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, HasAdminSecret]

    def post(self, request):
        data: dict = request.data
        action = data["action"]
        user = self.request.user

        if action == "set_subscription":
            sub = data["subscription"]
            additional_limits = {}
            if sub == "Pay as you go":
                additional_limits = {
                    "granted_words_simple_scan": 300000
                }
            user.subscription = sub
            user.used_words_simple_scan = 0
            user.additional_limits = additional_limits

        if action == "set_used_words":
            user.used_words_simple_scan = data["words_used"]

        if action == "remove_subscription":
            user.subscription = "Free"
            user.premium_or_custom_available_until = None
            user.additional_limits = {}
            StripeSubscription.objects.filter(user=user).delete()

        if action == "set_overrides":
            options = user.options
            overrides = {**(options.overrides or {}), **data["overrides"]}
            overrides = {k: v for k, v in overrides.items() if v != [None]}
            options.overrides = overrides
            options.save()

        if action == "reset_overrides":
            options = user.options
            options.overrides = {}
            options.save()

        user.save()

        return success_response()
