"""
Django settings for Own Firebase (ownfirebase) project.
Phase 1 MVP: Multi-tenant by project, PostgreSQL + Redis, DRF auth scaffold.
"""

import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ['DJANGO_SECRET_KEY']

DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

INSTALLED_APPS = [
    'daphne',  # ASGI server for Channels (must be first)
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'drf_spectacular',
    'django_filters',
    'django_celery_beat',
    'django_celery_results',
    'storages',
    'channels',

    # Project apps
    'core',
    'api',
    'data',
    'rules',
    'realtime',
    'storage',
    'functions',
    'push',
    'analytics',
    'crashlytics',
    'config.apps.ConfigAppConfig',
    'enhanced_auth.apps.EnhancedAuthConfig',
    'app_check.apps.AppCheckConfig',
    'social_auth.apps.SocialAuthConfig',
    'abtesting.apps.ABTestingConfig',
    'ai.apps.AIConfig',
    'rag.apps.RAGConfig',
    'webhooks.apps.WebhooksConfig',
    'billing.apps.BillingConfig',
    'remoteconfig.apps.RemoteConfigApp',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.MultiTenantMiddleware',
]

ROOT_URLCONF = 'ownfirebase.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'ownfirebase.wsgi.application'
ASGI_APPLICATION = 'ownfirebase.asgi.application'

# Database: PostgreSQL with RLS (Row-Level Security) in production/docker; SQLite for development/testing
USE_POSTGRES = os.getenv('USE_POSTGRES', 'False') == 'True'
if USE_POSTGRES:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DATABASE_NAME', 'ownfirebase'),
            'USER': os.getenv('DATABASE_USER', 'postgres'),
            'PASSWORD': os.getenv('DATABASE_PASSWORD', 'postgres'),
            'HOST': os.getenv('DATABASE_HOST', 'localhost'),
            'PORT': os.getenv('DATABASE_PORT', '5432'),
            'ATOMIC_REQUESTS': True,
            'CONN_MAX_AGE': 600,
        }
    }
    # Second alias, same physical database, for bulk cross-tenant maintenance
    # jobs (e.g. storage.tasks.cleanup_pending_uploads) that can't operate
    # under a single tenant_context() (core/rls.py). Only added when a
    # BYPASSRLS role is actually configured — see core/migrations/0004_postgres_rls.py
    # for why FORCE ROW LEVEL SECURITY otherwise blocks these queries entirely.
    MAINTENANCE_DATABASE_USER = os.getenv('MAINTENANCE_DATABASE_USER')
    if MAINTENANCE_DATABASE_USER:
        DATABASES['maintenance'] = {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DATABASE_NAME', 'ownfirebase'),
            'USER': MAINTENANCE_DATABASE_USER,
            'PASSWORD': os.getenv('MAINTENANCE_DATABASE_PASSWORD', ''),
            'HOST': os.getenv('DATABASE_HOST', 'localhost'),
            'PORT': os.getenv('DATABASE_PORT', '5432'),
            'CONN_MAX_AGE': 600,
        }
else:
    # Fallback to SQLite for local dev/testing
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Redis: channel layer, cache, broker, presence
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Channels: WebSocket & realtime via Redis
if os.environ.get('REDIS_URL'):
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [REDIS_URL],
            },
        },
    }
else:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }

# Celery: background tasks & scheduling
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes

# Celery Beat: scheduled tasks
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'core.backends.CustomJWTAuthentication',  # Custom backend with blacklist support
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'core.pagination.DefaultCursorPagination',
    'PAGE_SIZE': 20,  # Phase 1 MVP: smaller page size for documents
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    # Cursor pagination for firestore-like keyset pagination
    'CURSOR_PAGINATION_TEMPLATE': 'rest_framework/pagination/numbers.html',
    # Rate for the 'login' throttle scope only (see core/throttling.LoginRateThrottle).
    # This does NOT enable throttling globally — no DEFAULT_THROTTLE_CLASSES is set here,
    # so only views/actions that explicitly reference a throttle with scope='login'
    # (i.e. AuthViewSet.login) are rate-limited.
    'DEFAULT_THROTTLE_RATES': {
        'login': '5/min',
    },
}

# JWT Settings (SimplJWT)
# Phase 1 MVP: 15-min access token, 7-day refresh token (Firebase-like TTLs)
SIMPLE_JWT = {
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': os.getenv('JWT_SIGNING_KEY', SECRET_KEY),
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),  # Firebase: 1 hour, but Phase 1 MVP uses shorter for dev
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),    # Firebase: 30 days
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'JTI_CLAIM': 'jti',
    'TOKEN_OBTAIN_SERIALIZER': 'api.serializers.CustomTokenObtainPairSerializer',
    'TOKEN_REFRESH_SERIALIZER': 'api.serializers.RefreshTokenSerializer',
}

# CORS
CORS_ALLOWED_ORIGINS = os.getenv(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:3000,http://localhost:8000'
).split(',')
CORS_ALLOW_CREDENTIALS = True

# drf-spectacular (OpenAPI schema)
SPECTACULAR_SETTINGS = {
    'TITLE': 'Own Firebase API',
    'DESCRIPTION': 'Multi-tenant Firestore alternative on Django + PostgreSQL',
    'VERSION': '0.1.0',
    'SERVE_PERMISSIONS': ['rest_framework.permissions.IsAuthenticated'],
    'SCHEMAS': {
        'default': {
            'class': 'drf_spectacular.openapi.AutoSchema',
        },
    },
}

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {name}: {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Storage: MinIO / S3 — always configure for presigned URL support in storage app
AWS_S3_ENDPOINT_URL = os.getenv('AWS_S3_ENDPOINT_URL', 'http://minio:9000')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', 'minioadmin')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', 'minioadmin')
AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'us-east-1')
AWS_S3_USE_SSL = os.getenv('AWS_S3_USE_SSL', 'False') == 'True'

if os.getenv('USE_S3', 'False') == 'True':
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME', 'ownfirebase')

# Multi-tenant context: set via middleware from JWT
# Stored in Django thread-local context for RLS enforcement
CONTEXT_VAR_PROJECT_ID = 'project_id'
CONTEXT_VAR_USER_ID = 'user_id'

# Push Notifications credentials
FCM_SERVER_KEY = os.environ.get('FCM_SERVER_KEY', '')
VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY', '')
VAPID_SUBJECT = os.environ.get('VAPID_SUBJECT', 'mailto:admin@example.com')
APNS_KEY_ID = os.environ.get('APNS_KEY_ID', '')
APNS_TEAM_ID = os.environ.get('APNS_TEAM_ID', '')
APNS_BUNDLE_ID = os.environ.get('APNS_BUNDLE_ID', '')
PUSH_QUEUE_KEY = 'ownfb:push:queue'

# Enhanced Auth settings
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', '')
MAGIC_LINK_BASE_URL = os.environ.get('MAGIC_LINK_BASE_URL', 'http://localhost:8000')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@ownfirebase.local')
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')

# Social Auth (Google, GitHub)
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GITHUB_CLIENT_ID = os.environ.get('GITHUB_CLIENT_ID', '')
GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET', '')

# Stripe billing (billing/stripe_service.py). STRIPE_API_BASE lets local dev
# and tests point at a stripe-mock instance instead of the real Stripe API.
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
STRIPE_API_BASE = os.environ.get('STRIPE_API_BASE', '')
STRIPE_PRICE_IDS = {
    'starter': os.environ.get('STRIPE_PRICE_STARTER', ''),
    'pro': os.environ.get('STRIPE_PRICE_PRO', ''),
    'enterprise': os.environ.get('STRIPE_PRICE_ENTERPRISE', ''),
}

# Sentry error tracking: no-op unless SENTRY_DSN is set in the environment.
# Safe to call unconditionally — init_sentry() decides whether to actually
# initialize, and never raises even if sentry-sdk isn't installed.
try:
    from core.observability import init_sentry
    init_sentry()
except Exception:
    import logging
    logging.getLogger(__name__).warning('Sentry initialization failed; continuing without it.', exc_info=True)
