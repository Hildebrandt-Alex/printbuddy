"""
PrintBuddy — Local Development Settings
SQLite, DEBUG=True, MOCK_GPU=True
"""
from .base import *  # noqa

# SQLite lokal — kein PostgreSQL-Server nötig
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Celery lokal — auch Redis auf localhost (oder TASK_ALWAYS_EAGER für Tests ohne Worker)
CELERY_BROKER_URL = 'redis://127.0.0.1:6379/0'
CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379/0'
CELERY_TASK_ALWAYS_EAGER = False  # True = Tasks synchron ausführen (kein Worker nötig)
CELERY_TASK_SERIALIZER = 'json'

# NAS-Pfad lokal
NAS_BASE_PATH = str(BASE_DIR / 'local_nas')

# Admin URL lokal
ADMIN_URL = 'pb-manage/'

# Email in Konsole ausgeben
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Lokaler NAS-Ersatz (Ordner simuliert NAS-Struktur)
import os
NAS_DIRS = [
    BASE_DIR / 'local_nas' / 'raw',
    BASE_DIR / 'local_nas' / 'exports' / 'pod',
    BASE_DIR / 'local_nas' / 'exports' / 'offset',
    BASE_DIR / 'local_nas' / 'exports' / 'preview',
    BASE_DIR / 'local_nas' / 'exports' / 'vector',
    BASE_DIR / 'local_nas' / 'gallery',
    BASE_DIR / 'local_nas' / 'bundles',
]
for _d in NAS_DIRS:
    os.makedirs(_d, exist_ok=True)

