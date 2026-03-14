"""
Django settings for tucker_and_dales_home_services project.
"""

from pathlib import Path
import environ

# =====================================================
# 🔧 CORE CONFIGURATION
# =====================================================
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BASE_DIR.parent

env = environ.Env(
    DEBUG=(bool, False),
)

env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(env_file)
    print(f"✅ Loaded environment from {env_file}")
else:
    print("⚠️ No .env file found — relying on system environment variables")

SITE_ID = env.int("SITE_ID", default=1)

# =====================================================
# 🔐 SECURITY / DEBUG
# =====================================================
SECRET_KEY = env("SECRET_KEY", default="dev-insecure-secret-key-change-me")
DEBUG = env.bool("DEBUG", default=False)

ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=["127.0.0.1", "localhost"],
)

CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=[],
)

# If DEBUG, force-add local origins so login POST doesn't 403
if DEBUG:
    local_origins = {
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "https://127.0.0.1:8000",
        "https://localhost:8000",
    }
    CSRF_TRUSTED_ORIGINS = list(set(CSRF_TRUSTED_ORIGINS) | local_origins)
else:
    if not CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS = [
            "https://*.herokuapp.com",
            "https://*.codeinstitute-ide.net",
        ]

# =====================================================
# 🔒 SSL / COOKIE BEHAVIOR
# =====================================================
# Behind proxies (Heroku). Safe locally too.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Match Gambinos pattern:
# no forced SSL redirect locally; only secure cookies in production
if DEBUG:
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
else:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# =====================================================
# 🪵 LOGGING
# =====================================================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name}: {message}",
            "style": "{",
        },
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
        "django": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": True,
        },
        "scheduling.availability": {
            "handlers": ["file", "console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

# =====================================================
# 🔌 APPLICATION DEFINITION
# =====================================================
INSTALLED_APPS = [
    # Django built-ins
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",

    # Local apps
    "core.apps.CoreConfig",
    "customers",
    "scheduling",
    "billing",

    # Third-party
    "widget_tweaks",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
]

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

ROOT_URLCONF = "tucker_and_dales_home_services.urls"
WSGI_APPLICATION = "tucker_and_dales_home_services.wsgi.application"

# =====================================================
# 🎨 TEMPLATES
# =====================================================
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [PROJECT_DIR / "templates", BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# =====================================================
# 🗄 DATABASE
# =====================================================
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    )
}

DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60)
DATABASES["default"].setdefault("OPTIONS", {})
DATABASES["default"]["OPTIONS"].setdefault("connect_timeout", 5)

if DATABASES["default"]["ENGINE"] != "django.db.backends.sqlite3":
    DATABASES["default"]["ATOMIC_REQUESTS"] = True

# =====================================================
# 🔐 AUTHENTICATION
# =====================================================
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        )
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        )
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        )
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        )
    },
]

# =====================================================
# 🔁 LOGIN / LOGOUT REDIRECTS
# =====================================================
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# =====================================================
# 🔐 DJANGO-ALLAUTH SETTINGS
# =====================================================
ACCOUNT_LOGIN_METHODS = {"username", "email"}

ACCOUNT_SIGNUP_FIELDS = [
    "email*",
    "username*",
    "password1*",
    "password2*",
]

ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_EMAIL_SUBJECT_PREFIX = "[Tucker & Dale's] "

ACCOUNT_CONFIRM_EMAIL_ON_GET = True
ACCOUNT_EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL = None
ACCOUNT_AUTHENTICATED_LOGIN_REDIRECTS = True
USE_X_FORWARDED_HOST = True
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https" if not DEBUG else "http"

# =====================================================
# 🌍 I18N / TIMEZONE
# =====================================================
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_TZ = True

# =====================================================
# 🧾 STATIC & MEDIA
# =====================================================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =====================================================
# 💳 STRIPE / GOOGLE MAPS
# =====================================================
STRIPE_PUBLISHABLE_KEY = env("STRIPE_PUBLISHABLE_KEY", default="")
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY", default="")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET", default="")
STRIPE_CURRENCY = env("STRIPE_CURRENCY", default="usd")

GOOGLE_MAPS_API_KEY = env("GOOGLE_MAPS_API_KEY", default="")
GOOGLE_MAPS_BROWSER_KEY = env("GOOGLE_MAPS_BROWSER_KEY", default="")
GOOGLE_MAPS_SERVER_KEY = env("GOOGLE_MAPS_SERVER_KEY", default="")

# =====================================================
# 📧 EMAIL CONFIGURATION
# =====================================================


def _clean_env_str(key: str, default: str = "") -> str:
    """
    Strip inline comments and whitespace from env values.
    Helps prevent SMTP auth bugs caused by copied values.
    """
    raw = env(key, default=default)
    if raw is None:
        return ""
    raw = str(raw)
    if "#" in raw:
        raw = raw.split("#", 1)[0]
    return raw.strip()


USE_CONSOLE_EMAIL = env.bool("USE_CONSOLE_EMAIL", default=False)

if DEBUG and USE_CONSOLE_EMAIL:
    # Local development: print emails to console
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    # Production or explicit SMTP testing
    EMAIL_BACKEND = env.str(
        "EMAIL_BACKEND",
        default="django.core.mail.backends.smtp.EmailBackend",
    )

EMAIL_HOST = env.str("EMAIL_HOST", default="smtp-relay.brevo.com")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)

EMAIL_HOST_USER = _clean_env_str("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = _clean_env_str("EMAIL_HOST_PASSWORD", default="")

DEFAULT_FROM_EMAIL = _clean_env_str(
    "DEFAULT_FROM_EMAIL",
    default="Tucker & Dale's Home Services <no-reply@tuckeranddales.com>",
)

SERVER_EMAIL = DEFAULT_FROM_EMAIL

# =====================================================
# 🗞️ NEWSLETTER / SITE CONFIG
# =====================================================
SITE_BASE_URL = _clean_env_str(
    "SITE_BASE_URL",
    default="http://127.0.0.1:8000",
)

if SITE_BASE_URL.endswith("/"):
    SITE_BASE_URL = SITE_BASE_URL.rstrip("/")
