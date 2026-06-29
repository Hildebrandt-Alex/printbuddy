#!/bin/bash
# PrintBuddy — Deploy Script
# Speicherort auf VPS: /opt/printbuddy/deploy.sh
# Aufruf: ssh user@vps 'bash /opt/printbuddy/deploy.sh'
# Rollback: git revert HEAD --no-edit && git push && ssh user@vps 'bash /opt/printbuddy/deploy.sh'

set -e  # Sofort abbrechen bei Fehler

cd /opt/printbuddy

echo "=== PrintBuddy Deploy $(date) ==="

# 1. Code holen
git pull origin main

# 2. Dependencies
source venv/bin/activate
pip install -r requirements.txt --quiet

# 3. Django vorbereiten
export DJANGO_SETTINGS_MODULE=printbuddy.settings.production
python manage.py migrate --run-syncdb
python manage.py collectstatic --noinput --clear

# 4. Services neustarten (eigene Namen — kein Konflikt mit anderen Projekten)
sudo systemctl restart gunicorn.printbuddy
sudo systemctl restart celery-printbuddy-gpu celery-printbuddy-cpu

# 5. Nginx Config prüfen und neuladen (nicht neu starten — unterbricht andere Projekte nicht)
sudo nginx -t && sudo systemctl reload nginx

echo "=== Deploy $(git rev-parse --short HEAD) abgeschlossen ==="
