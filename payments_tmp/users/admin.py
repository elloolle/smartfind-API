from django.conf import settings
from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.contrib.auth import decorators, get_user_model
from django.utils.translation import gettext_lazy as _
from bitapi.payments.models import StripeSubscription
from bitapi.users.models import SubscribeRequest, Questionnaire, SocialMediaSubscribeRequest, UserOptions
from bitapi.users.forms import UserAdminChangeForm, UserAdminCreationForm
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

if settings.DJANGO_ADMIN_FORCE_ALLAUTH:
    # Force the `admin` sign in process to go through the `django-allauth` workflow:
    # https://django-allauth.readthedocs.io/en/stable/advanced.html#admin
    admin.site.login = decorators.login_required(admin.site.login)  # type: ignore[method-assign]


@admin.register(User)
class UserAdmin(auth_admin.UserAdmin):
    form = UserAdminChangeForm
    add_form = UserAdminCreationForm
    search_fields = ["username", "email"]
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("name", "email")}),
        (_("Subscription info"), {"fields": (
            "used_words_simple_scan",
            "subscription",
            "premium_or_custom_available_until",
            "enrolled",
            "onboarding_completed",
            "role",
            "subscription_start_date"
        )}),
        (_("Anonymous User"), {"fields": ("is_anon", "registered_user")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    list_display = [
        "username",
        "name",
        "is_superuser",
        "used_words_simple_scan",
        "registration_type",
        "is_anon",
        "registered_user"
    ]

@admin.register(UserOptions)
class UserOptionsAdmin(admin.ModelAdmin):
    list_display = ["user", "policy_accepted", "policy_timestamp", "policy_ip", "policy_version"]
    search_fields = ["user__username", "user__name"]

@admin.register(Questionnaire)
class QuestionnaireAdmin(admin.ModelAdmin):
    list_display = ["user", "work_place", "discovery_source"]
    search_fields = ["user__username", "work_place", "discovery_source"]


@admin.register(SocialMediaSubscribeRequest)
class SocialMediaSubscribeRequestAdmin(admin.ModelAdmin):
    list_display = ["user", "source", "link_url", "created_at", "approved"]
    list_filter = ["source", "approved", "created_at"]
    search_fields = ["user__username", "user__name", "link_url"]
    actions = ["approve_requests"]

    def approve_requests(self, request, queryset):
        for social_request in queryset:
            if not social_request.approved:
                social_request.approved = True
                social_request.save()

        self.message_user(request, f"{queryset.count()} requests were approved and users received Premium subscription.")

    approve_requests.short_description = "Approve selected requests and grant Premium subscription"

admin.site.register(StripeSubscription)
