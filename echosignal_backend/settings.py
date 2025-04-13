# /echosignal_project/echosignal_backend/settings.py

import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional

# --- Basic Logging Setup (Configure before extensive use) ---
# Configure logging early to capture potential issues during settings load.
# Basic console logging setup initially. More detailed config later in the file.
logging.basicConfig(level=logging.INFO, format='%(levelname)s %(asctime)s %(module)s %(message)s')
logger = logging.getLogger(__name__) # Logger for settings file itself
# Or use a project-specific logger: logger = logging.getLogger('echosignal.settings')

logger.info("Initializing Django settings...")

# --- Prometheus Metrics Integration (Optional) ---
PROMETHEUS_ENABLED: bool = False
try:
    from prometheus_client import Counter, Gauge
    # Define metrics: Initialized once when settings are loaded.
    SETTINGS_LOAD_COUNT = Counter(
        'django_settings_loads_total',
        'Total times the Django settings module was loaded.'
    )
    DEBUG_MODE_GAUGE = Gauge(
        'django_debug_mode',
        'Indicates if Django DEBUG mode is enabled (1 for True, 0 for False).'
    )
    PROMETHEUS_ENABLED = True
    logger.info("Prometheus client library found. Metrics enabled.")
    SETTINGS_LOAD_COUNT.inc() # Increment on each settings load
except ImportError:
    logger.warning("Prometheus client library not found or import failed. Prometheus metrics disabled.")
    # Define dummy metrics if needed to avoid NameErrors later, or use guards
    class DummyMetric:
        def set(self, *args, **kwargs): pass
        def inc(self, *args, **kwargs): pass
    DEBUG_MODE_GAUGE = DummyMetric()


# --- Core Paths ---
BASE_DIR: Path = Path(__file__).resolve().parent.parent
logger.debug(f"Project BASE_DIR: {BASE_DIR}")


# --- Environment Variable Loading ---
# Load .env file IF IT EXISTS. Primarily for local development.
# PRODUCTION ENVIRONMENTS SHOULD PROVIDE VARIABLES DIRECTLY.
dotenv_path: Path = BASE_DIR / '.env'
loaded_dotenv: bool = load_dotenv(dotenv_path=dotenv_path)

if loaded_dotenv:
    logger.info(f"Loaded environment variables from: {dotenv_path}")
# Warn if .env is loaded in a potentially non-debug environment later


# --- Core Security Settings ---
# https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECRET_KEY: MUST be set in the environment for production.
SECRET_KEY: str
try:
    SECRET_KEY = os.environ['SECRET_KEY']
    # Avoid logging the key itself, even at debug level
    logger.debug("SECRET_KEY loaded successfully from environment.")
except KeyError:
    logger.critical("CRITICAL: SECRET_KEY environment variable not set!")
    raise KeyError("SECRET_KEY environment variable not set. This is required.")

# DEBUG: Defaults to False. MUST be False in production.
# Set DEBUG=1 in your environment ONLY for local development.
DEBUG: bool = os.getenv('DEBUG', '0') == '1'
logger.info(f"DEBUG mode: {DEBUG}")
DEBUG_MODE_GAUGE.set(1 if DEBUG else 0)

if DEBUG:
    logger.warning("SECURITY WARNING: DEBUG is enabled! Ensure this is NOT a production environment.")
elif loaded_dotenv:
     logger.warning(f"Loaded .env file ({dotenv_path}) while DEBUG is False. Ensure production uses environment variables directly.")

# ALLOWED_HOSTS: MUST be configured with your domain(s) in production.
# Read from env var as a comma-separated string (e.g., "echosignal.org,www.echosignal.org")
allowed_hosts_str: Optional[str] = os.getenv('ALLOWED_HOSTS')
ALLOWED_HOSTS: List[str] = allowed_hosts_str.split(',') if allowed_hosts_str else []

if not DEBUG and not ALLOWED_HOSTS:
    logger.critical("CRITICAL: ALLOWED_HOSTS is empty and DEBUG is False. Application will not be accessible.")
    # Consider raising an ImproperlyConfigured error here if desired
    # raise ImproperlyConfigured("ALLOWED_HOSTS must be set in production (when DEBUG=False).")
logger.info(f"ALLOWED_HOSTS: {ALLOWED_HOSTS}")


# --- Application Definition ---
DJANGO_APPS: List[str] = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles', # Required for static files handling
]
THIRD_PARTY_APPS: List[str] = [
    # Add any third-party apps here (e.g., 'rest_framework', 'django_prometheus')
    # 'django_prometheus', # Example: Uncomment if using django-prometheus for metrics endpoint
]
PROJECT_APPS: List[str] = [
    'articles.apps.ArticlesConfig', # Use AppConfig for clarity
]
INSTALLED_APPS: List[str] = DJANGO_APPS + THIRD_PARTY_APPS + PROJECT_APPS
logger.debug(f"Installed apps: {INSTALLED_APPS}")


# --- Middleware ---
# https://docs.djangoproject.com/en/5.0/ref/middleware/
# Order matters. Security middleware often comes first.
MIDDLEWARE: List[str] = [
    'django.middleware.security.SecurityMiddleware',
    # Whitenoise for static files (efficiently serving static files in production)
    # Place after SecurityMiddleware but before most others
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 'django_prometheus.middleware.PrometheusBeforeMiddleware', # Example: If using django-prometheus
    # 'django_prometheus.middleware.PrometheusAfterMiddleware',  # Example: If using django-prometheus
]

# --- URL Configuration ---
ROOT_URLCONF: str = 'echosignal_backend.urls'

# --- Templates ---
# https://docs.djangoproject.com/en/5.0/topics/templates/

# Base options common to both DEBUG and non-DEBUG
template_options: Dict[str, Any] = {
    'context_processors': [
        'django.template.context_processors.debug',
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
    ],
}

# Determine APP_DIRS and potentially add loaders based on DEBUG status
APP_DIRS_ENABLED: bool = True # Default for DEBUG=True
if not DEBUG:
    # In production (not DEBUG), disable APP_DIRS shortcut and define loaders explicitly
    APP_DIRS_ENABLED = False
    template_options['loaders'] = [ # Add 'loaders' key only when not DEBUG
        ('django.template.loaders.cached.Loader', [
            'django.template.loaders.filesystem.Loader',
            # Explicitly include app directories loader here when using 'loaders'
            'django.template.loaders.app_directories.Loader',
        ]),
    ]
# Log the decision
logger.debug(f"Template config: APP_DIRS={APP_DIRS_ENABLED}, Loaders defined={not APP_DIRS_ENABLED}")

TEMPLATES: List[Dict[str, Any]] = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': APP_DIRS_ENABLED, # Set based on DEBUG status
        'OPTIONS': template_options, # Contains 'loaders' only if not DEBUG
    },
]

# --- WSGI Application ---
# https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
WSGI_APPLICATION: str = 'echosignal_backend.wsgi.application'


# --- Database ---
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases
# Database configuration MUST be read from environment variables in production.
DATABASES: Dict[str, Dict[str, str]]
try:
    db_name = os.environ['DATABASE_NAME']
    db_user = os.environ['DATABASE_USER']
    db_password = os.environ['DATABASE_PASSWORD'] # Avoid logging password
    db_host = os.environ['DATABASE_HOST']
    db_port = os.environ['DATABASE_PORT']

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': db_name,
            'USER': db_user,
            'PASSWORD': db_password,
            'HOST': db_host,
            'PORT': db_port,
            # Production considerations:
            # 'CONN_MAX_AGE': 600,  # Optional: Persistent connections (seconds)
            # 'OPTIONS': {
            #     'sslmode': 'require', # Optional: Enforce SSL if DB requires it
            # },
        }
    }
    logger.info(f"Database configured: Engine=postgresql, Name={db_name}, User={db_user}, Host={db_host}, Port={db_port}")
except KeyError as e:
    logger.critical(f"CRITICAL: Database configuration environment variable missing: {e}. Check environment.")
    raise KeyError(f"Database configuration environment variable missing: {e}. Check environment.")


# --- Password Validation ---
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS: List[Dict[str, str]] = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]


# --- Internationalization ---
# https://docs.djangoproject.com/en/5.0/topics/i18n/
LANGUAGE_CODE: str = 'en-us'
TIME_ZONE: str = 'UTC'
USE_I18N: bool = True
USE_TZ: bool = True # Recommended for handling datetimes correctly


# --- Static Files (CSS, JavaScript, Images) ---
# https://docs.djangoproject.com/en/5.0/howto/static-files/
# https://whitenoise.readthedocs.io/en/stable/
STATIC_URL: str = '/static/' # URL path prefix for static files
STATIC_ROOT: Path = BASE_DIR / 'staticfiles' # Directory where `collectstatic` gathers files for deployment. MUST be defined for production.
# Optional: Define directories where Django looks for static files besides app's static/ dirs
STATICFILES_DIRS: List[Path] = [BASE_DIR / "static"]

# Whitenoise configuration (stores compressed and versioned files)
# Ensure 'whitenoise.middleware.WhiteNoiseMiddleware' is in MIDDLEWARE
STATICFILES_STORAGE: str = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
logger.info(f"Static files configured: STATIC_URL={STATIC_URL}, STATIC_ROOT={STATIC_ROOT}, Storage={STATICFILES_STORAGE}")


# --- Default Primary Key Field Type ---
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD: str = 'django.db.models.BigAutoField'


# --- Logging Configuration (Detailed) ---
# Overrides the basicConfig done earlier.
LOGGING: Dict[str, Any] = {
    'version': 1,
    'disable_existing_loggers': False, # Keep Django's default loggers active
    'formatters': {
        'verbose': {
            # Include more context for production debugging if needed
            'format': '{levelname} {asctime} {name} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            # Standard format for console/container logs
            'format': '{levelname} {asctime} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            # Log INFO level and above to console (stderr/stdout)
            'level': os.getenv('DJANGO_CONSOLE_LOG_LEVEL', 'INFO'),
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        # Example File Handler (Uncomment and configure if needed for production)
        # 'file': {
        #     'level': 'INFO',
        #     'class': 'logging.handlers.RotatingFileHandler', # Use rotating file handler
        #     'filename': BASE_DIR / 'logs/django.log', # Ensure logs directory exists and has write permissions
        #     'maxBytes': 1024*1024*5, # 5 MB
        #     'backupCount': 5,
        #     'formatter': 'verbose',
        # },
    },
    'loggers': {
        'django': { # Configure Django's internal logs
            'handlers': ['console'], # Add 'file' here if using file logging
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'), # Control Django log level via env
            'propagate': False, # Don't pass Django logs to the root logger unless needed
        },
        'django.request': { # Specific logger for request handling
             'handlers': ['console'], # Add 'file' here if using file logging
             'level': os.getenv('DJANGO_REQUEST_LOG_LEVEL', 'WARNING'), # Log only >= WARNING for requests by default
             'propagate': False,
        },
        'echosignal': { # Logger for our specific project code (e.g., 'echosignal.views', 'echosignal.tasks')
            'handlers': ['console'], # Add 'file' here if using file logging
            'level': os.getenv('APP_LOG_LEVEL', 'INFO'), # Control App log level via env
            'propagate': True, # Allow passing logs to parent/root if needed
        },
        # Example: Configure logging for a specific app like 'articles'
        # 'articles': {
        #     'handlers': ['console'],
        #     'level': 'INFO', # Default INFO for specific apps
        #     'propagate': True,
        # },
    },
    # Optional: Configure root logger if you want to catch logs not handled above
    # 'root': {
    #     'handlers': ['console'],
    #     'level': 'WARNING',
    # },
}
logger.info("Detailed logging configured.")


# --- Production Security Settings (HTTPS) ---
# These settings are typically enabled only when not in DEBUG mode and behind HTTPS.
# Ensure your deployment setup (e.g., Nginx, Load Balancer) handles TLS termination.
# SECURE_SSL_REDIRECT: bool = not DEBUG
# SESSION_COOKIE_SECURE: bool = not DEBUG
# CSRF_COOKIE_SECURE: bool = not DEBUG
# SECURE_HSTS_SECONDS: int = 31536000 if not DEBUG else 0 # 1 year, enable carefully after testing
# SECURE_HSTS_INCLUDE_SUBDOMAINS: bool = not DEBUG
# SECURE_HSTS_PRELOAD: bool = not DEBUG
# SECURE_BROWSER_XSS_FILTER: bool = True
# SECURE_CONTENT_TYPE_NOSNIFF: bool = True
# X_FRAME_OPTIONS: str = 'DENY' # Already default in recent Django, but explicit is fine

# --- Final Log ---
logger.info("Django settings loading process completed.")