from pathlib import Path
import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

ROOT_URLCONF = "smartfindAPI.urls"


TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "smartfindAPI.wsgi.application"


AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


STATIC_URL = "static/"


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SECRET_KEY = "django-insecure-svr-u2ps=pu^j_d5cq75+%7g$=7aj59_)@g1%^u=!64ni9@01^"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "users",
    "embeddings",
    "rest_framework_simplejwt",
    "subscription_payments",
    "djstripe",
]


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication"
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
}

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
AUTH_USER_MODEL = "users.User"


SIMPLE_JWT = {
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
    "UPDATE_LAST_LOGIN": False,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": "",
    "AUDIENCE": None,
    "ISSUER": None,
    "JSON_ENCODER": None,
    "JWK_URL": None,
    "LEEWAY": 0,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "USER_AUTHENTICATION_RULE": "rest_framework_simplejwt.authentication.default_user_authentication_rule",
    "ON_LOGIN_SUCCESS": "rest_framework_simplejwt.serializers.default_on_login_success",
    "ON_LOGIN_FAILED": "rest_framework_simplejwt.serializers.default_on_login_failed",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "TOKEN_USER_CLASS": "rest_framework_simplejwt.models.TokenUser",
    "JTI_CLAIM": "jti",
    "SLIDING_TOKEN_REFRESH_EXP_CLAIM": "refresh_exp",
    "SLIDING_TOKEN_LIFETIME": timedelta(minutes=5),
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=1),
    "TOKEN_OBTAIN_SERIALIZER": "rest_framework_simplejwt.serializers.TokenObtainPairSerializer",
    "TOKEN_REFRESH_SERIALIZER": "rest_framework_simplejwt.serializers.TokenRefreshSerializer",
    "TOKEN_VERIFY_SERIALIZER": "rest_framework_simplejwt.serializers.TokenVerifySerializer",
    "TOKEN_BLACKLIST_SERIALIZER": "rest_framework_simplejwt.serializers.TokenBlacklistSerializer",
    "SLIDING_TOKEN_OBTAIN_SERIALIZER": "rest_framework_simplejwt.serializers.TokenObtainSlidingSerializer",
    "SLIDING_TOKEN_REFRESH_SERIALIZER": "rest_framework_simplejwt.serializers.TokenRefreshSlidingSerializer",
}


EMBEDDINGS_API_KEYS = {
    "openai": os.environ["OPENAI_API_KEY"],
    "google": os.environ["GOOGLE_API_KEY"],
    "openrouter": os.environ["OPENROUTER_API_KEY"],
    "morphllm": os.environ["MORPHLM_API_KEY"],
}
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MORPHLM_BASE_URL = "https://api.morphllm.com/v1"
EMBEDDING_MODELS = {
    "openai": {
        "method": "",
        "models": [
            "text-embedding-3-small",
            "text-embedding-3-large",
            "text-embedding-ada-002",
        ],
    },
    "google": {"method": "", "models": ["gemini-embedding-001"]},
    "openrouter": {
        "method": "",
        "models": [
            "mistralai/mistral-embed-2312",
            "mistralai/codestral-embed-2505",
            "google/gemini-embedding-001",
            "openai/text-embedding-ada-002",
            "openai/text-embedding-3-large",
            "openai/text-embedding-3-small",
            "qwen/qwen3-embedding-8b",
        ],
    },
    "morphllm": {
        "method": "",
        "models": ["morph-embedding-v3"],
        "min_dimension": 1024,
        "max_dimension": 1024,
    },
}

STRIPE_LIVE_SECRET_KEY = os.environ["LIVE_STRIPE_API_KEY"]
STRIPE_TEST_SECRET_KEY = os.environ["TEST_STRIPE_API_KEY"]
STRIPE_LIVE_MODE = False

DJSTRIPE_FOREIGN_KEY_TO_FIELD = "id"
DJSTRIPE_WEBHOOK_SECRET = os.environ["TEST_STRIPE_WEBHOOK_KEY"]
