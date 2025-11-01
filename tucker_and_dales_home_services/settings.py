"""
Django settings for tucker_and_dales_home_services project.
"""

from pathlib import Path
import os
import environ
from dotenv import load_dotenv

# =====================================================
# 🔧 CORE CONFIGURATION
# =====================================================
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, False))
DEBUG = False

env_file = BASE_DIR / ".env"
if env_file.exists():
    env.read_env(env_file)
    print(f"✅ Loaded environment from {env_file}")
else:
    print("⚠️ No .env file found — relying on system environment variables (Heroku)")

SECRET_KEY = env("SECRET_KEY", default="unsafe-secret-key")
ALLOWED_HOSTS = ["*"]

# =====================================================
# 🧩 INSTALLED APPS
# =====================================================
INSTALLED_APPS = [
    # Django built-ins
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",  # ✅ only once

    # Local apps
    "core",
    "customers",
    "scheduling",
    "billing",

    # Third-party
    "widget_tweaks",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
]

SITE_ID = int(os.getenv("SITE_ID", "1"))

# =====================================================
# ⚙️ MIDDLEWARE
# =====================================================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# =====================================================
# 🧱 TEMPLATES
# =====================================================
ROOT_URLCONF = "tucker_and_dales_home_services.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "billing.context_processors.cart_summary",
            ],
        },
    },
]

WSGI_APPLICATION = "tucker_and_dales_home_services.wsgi.application"

# =====================================================
# 🗄 DATABASE
# =====================================================
DATABASES = {
    "default": env.db("DATABASE_URL")
}

# =====================================================
# 🔐 AUTHENTICATION
# =====================================================
AUTHENTICATION_BACKENDS = [
    "core.backends.EmailOrUsernameModelBackend",  # custom
    "django.contrib.auth.backends.ModelBackend",  # default
    "allauth.account.auth_backends.AuthenticationBackend",  # allauth
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# =====================================================
# 🌍 I18N / TIMEZONE
# =====================================================
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# =====================================================
# 🧾 STATIC & MEDIA
# =====================================================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# =====================================================
# 🪵 LOGGING
# =====================================================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "[{asctime}] {levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "file": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "django.log",
            "formatter": "verbose",
        },
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {"handlers": ["file", "console"], "level": "INFO", "propagate": True},
        "scheduling.availability": {
            "handlers": ["file", "console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

# =====================================================
# 🔁 LOGIN / LOGOUT REDIRECTS
# =====================================================
LOGIN_URL = "/customers/register/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# =====================================================
# 💳 STRIPE / GOOGLE MAPS
# =====================================================
STRIPE_PUBLISHABLE_KEY = env("STRIPE_PUBLISHABLE_KEY", default="")
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY", default="")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET", default="")
STRIPE_CURRENCY = "usd"

GOOGLE_MAPS_API_KEY = env("GOOGLE_MAPS_API_KEY", default="")
GOOGLE_MAPS_BROWSER_KEY = env("GOOGLE_MAPS_BROWSER_KEY", default="")
GOOGLE_MAPS_SERVER_KEY = env("GOOGLE_MAPS_SERVER_KEY", default="")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =====================================================
# 📨 EMAIL CONFIGURATION (Local + Heroku)
# =====================================================
load_dotenv(BASE_DIR / ".env")

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL",
    f"Tucker & Dale’s <{EMAIL_HOST_USER or 'no-reply@localhost'}>",
)
SERVER_EMAIL = os.getenv("SERVER_EMAIL", EMAIL_HOST_USER)

# Console backend in debug mode
if os.getenv("DJANGO_DEBUG", "False") == "True":
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# =====================================================
# 🔐 DJANGO-ALLAUTH SETTINGS
# =====================================================
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "username*", "password1*", "password2*"]
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_EMAIL_SUBJECT_PREFIX = "[Tucker & Dale’s] "
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https"  # change to http for localhost
