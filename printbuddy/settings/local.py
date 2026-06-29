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

# Django Debug Toolbar (optional, nur lokal)
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
