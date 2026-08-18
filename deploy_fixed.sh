#!/bin/bash
set -e
cd /opt/printbuddy

# WICHTIG: Production Settings explizit setzen!
export DJANGO_SETTINGS_MODULE=printbuddy.settings.production

git pull origin main
source venv/bin/activate
pip install -r requirements.txt --quiet

# Alle Django-Commands verwenden jetzt automatisch production settings
python manage.py migrate --run-syncdb
python manage.py collectstatic --noinput --clear

sudo systemctl restart gunicorn
sudo systemctl restart celery-printbuddy-gpu celery-printbuddy-cpu

echo "Deploy $(git rev-parse --short HEAD) abgeschlossen (PostgreSQL)"
