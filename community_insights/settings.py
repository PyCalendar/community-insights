"""Settings, configured with environment variables.

Settings, configured with environment variables (django-environ); see
docs/reference/configuration.rst for all of them.
"""

# The type hints of django-environ allow no defaults (default: NoValue) and return a union of
# all types; the values are checked by Django and the system checks instead.
# pyright: reportArgumentType=false, reportReturnType=false

import sys
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env()
DATA_DIR = Path(env("DATA_DIR", default=str(BASE_DIR / "data")))
TESTING = "pytest" in sys.modules or "behave" in sys.argv


def kept_secret(name: str) -> str:
    """A secret from the environment, or generated once into the data directory.

    A secret from the environment, or generated once into the data directory, the same for `make
    run` and the container.
    """
    if env(name, default=""):
        return env(name)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / name.lower()
    if not path.exists():
        from django.core.management.utils import get_random_secret_key

        path.write_text(get_random_secret_key())
        path.chmod(0o600)
    return path.read_text().strip()


DEBUG = env.bool("DEBUG", default=False)
# A site others can reach: default passwords stop it from starting
# (manage.py check_production). Local tests set PRODUCTION=false. Not DEBUG.
PRODUCTION = env.bool("PRODUCTION", default=True)
SECRET_KEY = kept_secret("SECRET_KEY")
# the stored GitHub tokens are encrypted with it (django-fernet-encrypted-fields)
SALT_KEY = kept_secret("SALT_KEY")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.github",
    "cachalot",
    "django_bootstrap5",
    "django_filters",
    "django_tables2",
    "health_check",
    "ordered_model",
    "community_insights",
]
try:  # development only: the browser tests (manage.py behave)
    import behave_django  # noqa: F401

    INSTALLED_APPS.append("behave_django")
except ImportError:
    pass

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",  # the language of the browser or chosen
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "community_insights.middleware.SafeTimezoneMiddleware",  # django-tz-detect
]
DEBUG_TOOLBAR = DEBUG and not TESTING
if DEBUG_TOOLBAR:
    try:
        import debug_toolbar  # noqa: F401
    except ImportError:
        DEBUG_TOOLBAR = False
if DEBUG_TOOLBAR:
    INSTALLED_APPS.append("debug_toolbar")
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
    INTERNAL_IPS = ["127.0.0.1"]

ROOT_URLCONF = "community_insights.urls"
WSGI_APPLICATION = "community_insights.wsgi.application"

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
                "community_insights.context.site",
            ],
        },
    },
]

DATABASES = {"default": env.db("DATABASE_URL", default=f"sqlite:///{DATA_DIR / 'db.sqlite3'}")}
DATABASES["default"]["CONN_MAX_AGE"] = 60
if DATABASES["default"]["ENGINE"].endswith("sqlite3"):
    # The web server and the worker write at the same time: wait for each other.
    DATABASES["default"].setdefault("OPTIONS", {}).update(
        {
            "timeout": 30,
            "transaction_mode": "IMMEDIATE",
            "init_command": "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;",
        }
    )
    # A file, not memory: the browser tests share it between server threads.
    DATABASES["default"]["TEST"] = {"NAME": str(DATA_DIR / "test-db.sqlite3")}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# The statistics read the same data again and again: django-cachalot keeps the
# answers of the database until the tables change. The cache is shared by all
# processes (gunicorn workers and the fetch worker), so it is never stale.
CACHES = {
    "default": env.cache(
        "CACHE_URL",
        default="locmemcache://" if TESTING else f"filecache://{DATA_DIR / 'cache'}",
    )
}
CACHALOT_ENABLED = env.bool("CACHALOT_ENABLED", default=True)

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
SITE_ID = 1
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/"

# Sign up with an email address and a password, or with GitHub. GitHub can be
# linked later (/accounts/3rdparty/) or a personal access token can be added.
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = env("ACCOUNT_EMAIL_VERIFICATION", default="optional")
ACCOUNT_UNIQUE_EMAIL = True
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_STORE_TOKENS = True  # the token is used to query GitHub
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True  # GitHub sign in with a known, verified email
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True

EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_BACKEND = (
    "django.core.mail.backends.smtp.EmailBackend"
    if EMAIL_HOST
    else "django.core.mail.backends.console.EmailBackend"
)
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="webmaster@localhost")
SOCIALACCOUNT_PROVIDERS = {
    "github": {
        # private repositories: asked only when somebody wants them (GitHub access)
        "SCOPE": env.list("GITHUB_SCOPE", default=["read:user"]),
        **(
            {
                "APP": {
                    "client_id": env("GITHUB_CLIENT_ID"),
                    "secret": env("GITHUB_SECRET", default=""),
                }
            }
            if env("GITHUB_CLIENT_ID", default="")
            else {}
        ),
    }
}

GITHUB_API = env("GITHUB_API", default="https://api.github.com")
# For now only public repositories: private ones are refused (errors/github.py).
PRIVATE_REPOSITORIES = env.bool("PRIVATE_REPOSITORIES", default=False)
# where the code and the documentation of the version that runs are
SOURCE_URL = env("SOURCE_URL", default="https://github.com/PyCalendar/community-insights")
DOCS_URL = env("DOCS_URL", default="https://community-insights.readthedocs.io/en/latest/")
# internal, external-http-container, external-separate-container, inline
# (community_insights/pipeline/modes.py)
FETCH_WORKER = env("FETCH_WORKER", default="internal")
FETCH_CONCURRENCY = env.int("FETCH_CONCURRENCY", default=4)  # jobs at the same time
GITHUB_MAX_CONCURRENT = env.int("GITHUB_MAX_CONCURRENT", default=20)  # requests

CACHE_KEEP_DAYS = env.int("CACHE_KEEP_DAYS", default=90)  # unused data is deleted after
DATABASE_MAX_MB = env.float("DATABASE_MAX_MB", default=1024)  # 1 GB; 0: no limit
DATABASE_MIN_AGE_HOURS = env.float("DATABASE_MIN_AGE_HOURS", default=24)  # never deleted for space
DJANGO_TABLES2_TEMPLATE = "django_tables2/bootstrap5-responsive.html"
TZ_DETECT_COUNTRIES = ()  # the time zone of the browser is enough

LANGUAGE_CODE = "en"
# The languages of the pages; the browser chooses, or the switch in the footer.
LANGUAGES = [("en", "English"), ("de", "Deutsch")]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
FORMS_URLFIELD_ASSUME_HTTPS = True  # the default of Django 6

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}
