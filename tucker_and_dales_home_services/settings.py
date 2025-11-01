"""
Django settings for tucker_and_dales_home_services project.
"""

import os
from pathlib import Path
import environ

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent.parent

# --- Environment setup ---
env = environ.Env(DEBUG=(bool, False))
# DEBUG = env.bool("DEBUG", default=False)
DEBUG = False

env_file = BASE_DIR / ".env"
if env_file.exists():
    env.read_env(env_file)
    print(f"✅ Loaded environment from {env_file}")
else:
    print("⚠️ No .env file found — relying on system environment variables (Heroku)")

# --- Security ---
SECRET_KEY = env("SECRET_KEY", default="unsafe-secret-key")

ALLOWED_HOSTS = ["*"]

# --- Installed Apps ---
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    # Local apps
    "core",
    "customers",
    "scheduling",
    "billing",
    "widget_tweaks",

    "allauth",
    "allauth.account",
    "allauth.socialaccount",

    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.github",

]

SITE_ID = int(os.getenv("SITE_ID", "1"))

# --- Middleware ---
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

MIDDLEWARE.insert(
    MIDDLEWARE.index(
        "django.contrib.auth.middleware.AuthenticationMiddleware") + 1,
    "allauth.account.middleware.AccountMiddleware",
)

ROOT_URLCONF = "tucker_and_dales_home_services.urls"

# --- Templates ---
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

# --- Database ---
DATABASES = {
    "default": env.db("DATABASE_URL")
}

# --- Authentication ---
AUTHENTICATION_BACKENDS = [
    "core.backends.EmailOrUsernameModelBackend",  # custom backend
    "django.contrib.auth.backends.ModelBackend",  # keep default
    "allauth.account.auth_backends.AuthenticationBackend",  # allauth

]


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# --- I18N / TZ ---
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# --- Static & Media ---
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# ⚙️ Stable WhiteNoise setup — tolerant (no crash on missing files)
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# --- Logging ---
logs_dir = BASE_DIR / "logs"
logs_dir.mkdir(exist_ok=True)

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

# --- Auth Redirects (Frontend vs Admin) ---
# where users get to Register / Sign-In modal
LOGIN_URL = "/customers/register/"
LOGIN_REDIRECT_URL = "/"                # redirect after successful login
LOGOUT_REDIRECT_URL = "/"               # redirect after logout

# --- Stripe ---
STRIPE_PUBLISHABLE_KEY = env("STRIPE_PUBLISHABLE_KEY", default="")
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY", default="")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET", default="")
STRIPE_CURRENCY = "usd"

# --- Google Maps ---
GOOGLE_MAPS_API_KEY = env("GOOGLE_MAPS_API_KEY", default="")
GOOGLE_MAPS_BROWSER_KEY = env("GOOGLE_MAPS_BROWSER_KEY", default="")
GOOGLE_MAPS_SERVER_KEY = env("GOOGLE_MAPS_SERVER_KEY", default="")

# --- Default Auto Field ---
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Staticfiles auto-detect for Heroku ---
# If running on Heroku (no local .env), always collect static.
# If running locally with .env, disable collectstatic.

if not (BASE_DIR / ".env").exists():
    # Heroku / production
    os.environ.setdefault("DISABLE_COLLECTSTATIC", "0")
else:
    # Local development
    os.environ.setdefault("DISABLE_COLLECTSTATIC", "1")
    print("🧩 Local dev mode: collectstatic disabled for speed.")

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"


# # Use email as primary login
# ACCOUNT_AUTHENTICATION_METHOD = "email"
# ACCOUNT_EMAIL_REQUIRED = True
# ACCOUNT_EMAIL_VERIFICATION = "mandatory"  # "none", "optional", or "mandatory"
# ACCOUNT_USERNAME_REQUIRED = False
# ACCOUNT_USER_MODEL_USERNAME_FIELD = None  # if your user model has no username

# # Redirect URLs
# LOGIN_REDIRECT_URL = "/"        # after login
# ACCOUNT_LOGOUT_REDIRECT_URL = "/"  # after logout

# # Signup / login flow tweaks
# ACCOUNT_SESSION_REMEMBER = True
# ACCOUNT_SIGNUP_PASSWORD_ENTER_TWICE = True
# ACCOUNT_UNIQUE_EMAIL = True
# ACCOUNT_LOGIN_ATTEMPTS_LIMIT = 5
# ACCOUNT_LOGIN_ATTEMPTS_TIMEOUT = 300  # seconds

# # Optional: auto-login after signup
# ACCOUNT_EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL = "/"
# Allauth behavior
# ✅ New login methods (replaces ACCOUNT_AUTHENTICATION_METHOD)
# allow both username and email login
ACCOUNT_LOGIN_METHODS = {"username", "email"}

# ✅ New-style signup fields (replaces ACCOUNT_EMAIL_REQUIRED)
# Use '*' to mark required fields
ACCOUNT_SIGNUP_FIELDS = ["username*", "email*", "password1*", "password2*"]

# ✅ Rate limiting (replaces ACCOUNT_LOGIN_ATTEMPTS_LIMIT/TIMEOUT)
ACCOUNT_RATE_LIMITS = {
    "login_failed": "5/5m",   # 5 failed logins per 5 minutes
    "signup": "10/h",         # optional rate limit for signups
}

ACCOUNT_EMAIL_VERIFICATION = "mandatory"  # can be "optional" or "none"
ACCOUNT_EMAIL_SUBJECT_PREFIX = "[Tucker & Dale’s] "
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_PRESERVE_USERNAME_CASING = False

# ✅ Redirects
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"
ACCOUNT_LOGOUT_ON_GET = True
ACCOUNT_SESSION_REMEMBER = True

# SMTP (only used if EMAIL_BACKEND is SMTP)
# ===========================
# ✉️ EMAIL SETTINGS
# ===========================
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER)
