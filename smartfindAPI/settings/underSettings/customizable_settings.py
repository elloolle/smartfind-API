from pathlib import Path

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "authentication",
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
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
}

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
AUTH_USER_MODEL = "authentication.User"


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',  # Specify the PostgreSQL backend
        'NAME': 'smartfind_db',  # Name of your PostgreSQL database
        'USER': 'admin',  # Username for connecting to the database
        'PASSWORD': 'admin',  # Password for the database user
        'HOST': 'localhost',  # Or the IP address/hostname of your PostgreSQL server
        'PORT': '5432',
    }
}
