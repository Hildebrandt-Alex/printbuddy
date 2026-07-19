"""
PrintBuddy — Base Settings
Gemeinsame Einstellungen für lokal und Produktion.
Alle Secrets kommen aus .env via django-environ.
"""
import environ
from pathlib import Path

# BASE_DIR zeigt auf das Root-Verzeichnis (wo manage.py liegt)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    LOCAL_DEV=(bool, False),
    MOCK_GPU=(bool, False),
    ALLOWED_HOSTS=(list, ['localhost', '127.0.0.1']),
)

# .env einlesen (existiert lokal, auf VPS manuell angelegt)
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
LOCAL_DEV = env('LOCAL_DEV')
MOCK_GPU = env('MOCK_GPU')
ALLOWED_HOSTS = env('ALLOWED_HOSTS')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # PrintBuddy Apps
    'gallery',
    'shop',
    'jobs',
    'studio',
    'gpu',
    'postprocess',
    'bundles',
    'etsy',
    'channels',
    'partners',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'printbuddy.urls'

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

WSGI_APPLICATION = 'printbuddy.wsgi.application'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'de-de'
TIME_ZONE = 'Europe/Berlin'
USE_I18N = True
USE_TZ = True

# UUID als Standard-PK
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Static & Media
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Celery
CELERY_BROKER_URL = env('REDIS_URL', default='redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = env('REDIS_URL', default='redis://127.0.0.1:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Europe/Berlin'

# Celery Queues
CELERY_TASK_ROUTES = {
    'gpu.tasks.*': {'queue': 'gpu_queue'},
    'postprocess.tasks.*': {'queue': 'cpu_queue'},
    'jobs.tasks.*': {'queue': 'cpu_queue'},
    'shop.tasks.*': {'queue': 'cpu_queue'},
    'bundles.tasks.*': {'queue': 'cpu_queue'},
    'partners.tasks.*': {'queue': 'cpu_queue'},
    'channels.tasks.*': {'queue': 'cpu_queue'},
}

# Stripe
STRIPE_SECRET_KEY = env('STRIPE_SECRET_KEY', default='')
STRIPE_WEBHOOK_SECRET = env('STRIPE_WEBHOOK_SECRET', default='')
STRIPE_PUBLISHABLE_KEY = env('STRIPE_PUBLISHABLE_KEY', default='')

# Printful
PRINTFUL_API_KEY = env('PRINTFUL_API_KEY', default='')

# RunPod
RUNPOD_API_KEY = env('RUNPOD_API_KEY', default='')
RUNPOD_ENDPOINT_ID = env('RUNPOD_ENDPOINT_ID', default='')  # FLUX Schnell/Dev
RUNPOD_SDXL_ENDPOINT_ID = env('RUNPOD_SDXL_ENDPOINT_ID', default='')  # SDXL 1.0
RUNPOD_UPSCALE_ENDPOINT = env('RUNPOD_UPSCALE_ENDPOINT', default='')

# Media-URL für externe API-Zugriffe (z.B. RunPod Img2Img)
MEDIA_URL_EXTERNAL = env('MEDIA_URL_EXTERNAL', default='https://printbuddy.datemyhobby.com/media')

# Vast.ai
VASTAI_API_KEY = env('VASTAI_API_KEY', default='')

# Etsy
ETSY_API_KEY = env('ETSY_API_KEY', default='')
ETSY_API_SECRET = env('ETSY_API_SECRET', default='')
ETSY_REDIRECT_URI = env('ETSY_REDIRECT_URI', default='')

# Email
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST', default='localhost')
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
EMAIL_PORT = 587
EMAIL_USE_TLS = True

# NAS Mount
NAS_MOUNT = env('NAS_MOUNT', default=str(BASE_DIR / 'local_nas'))
NAS_BASE_PATH = env('NAS_BASE_PATH', default=str(BASE_DIR / 'local_nas'))

# Auth
LOGIN_URL = '/studio/login/'
LOGIN_REDIRECT_URL = '/studio/'
LOGOUT_REDIRECT_URL = '/studio/login/'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {'format': '{levelname} {asctime} {module} {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'verbose'},
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
    },
}
