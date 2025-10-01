"""
Django settings for tucker_and_dales_home_services project.
"""

import os
from pathlib import Path
import environ

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent.parent

# --- Env setup ---

env = environ.Env(
    DEBUG=(bool, False)
)

env_file = os.path.join(BASE_DIR, ".env")
if os.path.exists(env_file):
    env.read_env(env_file)  # now uses the Env() object you just created
else:
    raise RuntimeError(f" .env file not found at {env_file}")


# --- Google Maps API ---
GOOGLE_MAPS_API_KEY = env("GOOGLE_MAPS_API_KEY", default="")

# --- Security ---
SECRET_KEY = env("SECRET_KEY", default="fallback-secret-key")
DEBUG = env("DEBUG", default=True)
ALLOWED_HOSTS = ["*"]  # adjust for production

# --- Installed apps ---
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # created apps
    "customers",
    "core",
    "scheduling",
]

# --- Middleware ---
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "tucker_and_dales_home_services.urls"

# --- Templates ---
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  # 👈 global /templates folder
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

WSGI_APPLICATION = "tucker_and_dales_home_services.wsgi.application"

# --- Database ---
DATABASES = {
    "default": env.db("DATABASE_URL")
}

# --- Auth ---
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

# --- Static files ---
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# --- Default PK ---
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Logging ---
logs_dir = BASE_DIR / "logs"
logs_dir.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "[{asctime}] {levelname} {name} {message}", "style": "{"},
        "simple": {"format": "{levelname} {message}", "style": "{"},
    },
    "handlers": {
        "django_file": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": logs_dir / "django.log",
            "formatter": "verbose",
        },
        "error_file": {
            "level": "ERROR",
            "class": "logging.FileHandler",
            "filename": logs_dir / "error.log",
            "formatter": "verbose",
        },
        "console": {
            "level": "WARNING",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "loggers": {
        "django": {"handlers": ["django_file", "error_file", "console"], "level": "INFO", "propagate": True},
        "core": {"handlers": ["django_file", "error_file"], "level": "DEBUG", "propagate": False},
        "customers": {"handlers": ["django_file", "error_file"], "level": "DEBUG", "propagate": False},
        "django.db.backends": {"handlers": ["django_file"], "level": "DEBUG", "propagate": False},
    },
}

# --- Login redirects ---
LOGIN_URL = "/admin/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/accounts/login/"
