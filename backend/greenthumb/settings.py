"""Django settings for Green Thumb.

Configuration comes from environment variables so the same code runs locally
and in production:

    DJANGO_DEBUG          "1" for development (default locally), "0" in production
    SECRET_KEY            required in production
    ALLOWED_HOSTS         comma-separated extra host names
    DATABASE_URL          optional; defaults to a local SQLite file
    STRIPE_SECRET_KEY     optional Stripe *test* key (sk_test_...); enables card payments in test mode
    STRIPE_WEBHOOK_SECRET optional; lets Stripe confirm payments via /stripe/webhook/

Locally, these can also go in backend/.env (one KEY=value per line; git-ignored).

On Render, the RENDER variable is set automatically, which switches the
defaults to production values.
"""
import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# Load backend/.env if present (local convenience). Real environment variables win.
_env_file = BASE_DIR / ".env"
if _env_file.exists():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        _key, _sep, _value = _line.strip().partition("=")
        if _sep and not _key.startswith("#"):
            os.environ.setdefault(_key.strip(), _value.strip().strip('"').strip("'"))

ON_RENDER = bool(os.environ.get("RENDER"))

DEBUG = os.environ.get("DJANGO_DEBUG", "0" if ON_RENDER else "1") == "1"

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    if not DEBUG:
        raise RuntimeError("Set the SECRET_KEY environment variable in production.")
    SECRET_KEY = "dev-only-insecure-key"  # local development only

ALLOWED_HOSTS = ["127.0.0.1", "localhost", ".onrender.com"] + [
    h.strip() for h in os.environ.get("ALLOWED_HOSTS", "").split(",") if h.strip()]
CSRF_TRUSTED_ORIGINS = ["https://*.onrender.com"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "store",      # the shop: catalog, cart, orders, reviews, accounts
    "insights",   # the data science dashboard
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise serves collected static files in production; in development
    # Django's runserver serves them directly.
    *([] if DEBUG else ["whitenoise.middleware.WhiteNoiseMiddleware"]),
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "greenthumb.urls"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]

WSGI_APPLICATION = "greenthumb.wsgi.application"

DATABASES = {
    # conn_health_checks: hosted Postgres (e.g. Neon) closes idle connections; check before reusing one.
    "default": dj_database_url.config(default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}", conn_max_age=600,
                                      conn_health_checks=True)
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "America/New_York"
USE_I18N = True
USE_TZ = True

LOGIN_URL = "login"

# Static files: app static folders + the shared product images in /assets.
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR.parent / "assets"]
STATIC_ROOT = BASE_DIR / "staticfiles"   # filled by `collectstatic` at deploy time (not committed)
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage" if DEBUG
                    else "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")   # Render terminates HTTPS at its proxy
    SECURE_SSL_REDIRECT = True
    # HSTS is left off on purpose: once browsers cache it, it cannot be undone quickly.

# Stripe Checkout (test mode only; see store/payments.py). Empty = checkout records orders without payment.
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
