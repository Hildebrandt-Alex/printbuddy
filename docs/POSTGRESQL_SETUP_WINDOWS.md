# PostgreSQL 15 Installation für Windows (Development)

## 🎯 Ziel: Lokal dieselbe DB wie Production

Production nutzt PostgreSQL 15, also installieren wir das gleiche lokal.

---

## 📥 Download & Installation

### 1. PostgreSQL 15 herunterladen

**URL:** https://www.enterprisedb.com/downloads/postgres-postgresql-downloads

**Version:** PostgreSQL 15.x für Windows x86-64

**Direktlink (Mai 2024):**
```
https://get.enterprisedb.com/postgresql/postgresql-15.6-1-windows-x64.exe
```

### 2. Installer ausführen

```
1. Setup-Typ: Server + Command Line Tools + pgAdmin 4
2. Installations-Pfad: C:\Program Files\PostgreSQL\15
3. Data-Verzeichnis: C:\Program Files\PostgreSQL\15\data
4. Port: 5432 (Default)
5. Superuser-Passwort: [SICHERES PASSWORT WÄHLEN]
   ⚠️ WICHTIG: Passwort notieren!
6. Locale: German, Germany (oder Default)
```

**Installation dauert:** ~5 Minuten

### 3. Installation verifizieren

```powershell
# Im Terminal (nach Installation):
psql --version
# Sollte zeigen: psql (PostgreSQL) 15.x
```

---

## 🔧 Datenbank & User erstellen

### 1. Öffne pgAdmin 4

**Start Menu → PostgreSQL 15 → pgAdmin 4**

Oder im Terminal:
```powershell
# Als postgres superuser verbinden
psql -U postgres
```

Passwort eingeben (das, was du bei Installation gewählt hast).

### 2. Development-Datenbank erstellen

```sql
-- Im psql oder pgAdmin Query Tool:

-- 1. User erstellen
CREATE USER printbuddy_dev WITH PASSWORD 'dev_password_123';

-- 2. Datenbank erstellen
CREATE DATABASE printbuddy_dev
    OWNER printbuddy_dev
    ENCODING 'UTF8'
    LC_COLLATE = 'German_Germany.1252'
    LC_CTYPE = 'German_Germany.1252'
    TEMPLATE template0;

-- 3. Rechte geben
GRANT ALL PRIVILEGES ON DATABASE printbuddy_dev TO printbuddy_dev;

-- 4. Verbindung testen
\c printbuddy_dev printbuddy_dev
-- Sollte erfolgreich verbinden

-- Fertig!
\q
```

### Alternative: Schnell-Script

Speichere als `setup_postgres_dev.sql`:

```sql
-- Development Setup für PrintBuddy
DROP DATABASE IF EXISTS printbuddy_dev;
DROP USER IF EXISTS printbuddy_dev;

CREATE USER printbuddy_dev WITH PASSWORD 'dev_password_123';

CREATE DATABASE printbuddy_dev
    OWNER printbuddy_dev
    ENCODING 'UTF8'
    TEMPLATE template0;

GRANT ALL PRIVILEGES ON DATABASE printbuddy_dev TO printbuddy_dev;

-- In PostgreSQL 15: PUBLIC Schema Rechte
\c printbuddy_dev
GRANT ALL ON SCHEMA public TO printbuddy_dev;
```

Ausführen:
```powershell
psql -U postgres -f setup_postgres_dev.sql
```

---

## 🔌 Django-Konfiguration anpassen

### 1. psycopg2 installieren

```powershell
# Im Projekt-venv:
pip install psycopg2-binary
```

### 2. .env anpassen

**Datei:** `.env` (im Projekt-Root)

```bash
# ══════════════════════════════════════════════════════════════════════════════
# DATABASE
# ══════════════════════════════════════════════════════════════════════════════

# VORHER (SQLite):
# DATABASE_URL=sqlite:///db.sqlite3

# NACHHER (PostgreSQL lokal):
DATABASE_URL=postgresql://printbuddy_dev:dev_password_123@localhost:5432/printbuddy_dev

# Production (unverändert):
# DATABASE_URL=postgresql://printbuddy_prod:PASSWORD@localhost:5432/printbuddy
```

### 3. Migrations ausführen

```powershell
# Alte SQLite DB sichern (falls vorhanden):
if (Test-Path db.sqlite3) {
    Copy-Item db.sqlite3 backups/db_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').sqlite3
}

# Migrations ausführen:
python manage.py migrate

# Superuser erstellen:
python manage.py createsuperuser
# Username: admin
# Email: deine@email.de
# Password: [SICHERES PASSWORT]

# Default Template erstellen:
python manage.py create_default_template

# Server starten:
python manage.py runserver
```

---

## ✅ Verifizierung

### 1. Django Check

```powershell
python manage.py check
# Sollte: System check identified no issues (0 silenced).
```

### 2. DB-Verbindung testen

```powershell
python manage.py dbshell
```

Sollte PostgreSQL Shell öffnen:
```
printbuddy_dev=> \dt
# Zeigt alle Django-Tabellen

printbuddy_dev=> SELECT COUNT(*) FROM jobs_pipelinetemplate;
# Sollte 1 zeigen (FLUX Schnell Standard)

printbuddy_dev=> \q
```

### 3. Admin öffnen

```
http://127.0.0.1:8000/admin/
```

Login mit Superuser → sollte funktionieren!

---

## 🔄 Production-Daten importieren (optional)

### Option A: Mit Management Command (empfohlen)

```powershell
python manage.py sync_prod_to_dev --confirm
```

⚠️ **WARNUNG:** Überschreibt lokale DB komplett!

### Option B: Manuell mit pg_dump

```powershell
# Auf VPS:
ssh datemyhobby "cd /opt/printbuddy && source venv/bin/activate && python manage.py dumpdata --natural-foreign --indent 2 > /tmp/prod_dump.json"

# Herunterladen:
scp datemyhobby:/tmp/prod_dump.json backups/

# Lokal importieren:
python manage.py loaddata backups/prod_dump.json
```

---

## 🛠️ Troubleshooting

### Problem: "psql nicht gefunden"

**Lösung:** PostgreSQL bin-Ordner zu PATH hinzufügen

```powershell
# Temporär (nur diese Session):
$env:Path += ";C:\Program Files\PostgreSQL\15\bin"

# Permanent (System-Eigenschaften → Umgebungsvariablen):
# PATH bearbeiten → Neu → C:\Program Files\PostgreSQL\15\bin
```

### Problem: "password authentication failed"

**Ursache:** Falsches Passwort oder User nicht erstellt

**Lösung:**
```powershell
psql -U postgres
# Passwort von Installation eingeben

# Dann im psql:
ALTER USER printbuddy_dev WITH PASSWORD 'dev_password_123';
```

### Problem: "FATAL: database does not exist"

**Lösung:**
```powershell
psql -U postgres
CREATE DATABASE printbuddy_dev OWNER printbuddy_dev;
\q
```

### Problem: Django kann nicht verbinden

**Check .env:**
```bash
# Muss exakt so aussehen:
DATABASE_URL=postgresql://printbuddy_dev:dev_password_123@localhost:5432/printbuddy_dev
```

**Check PostgreSQL läuft:**
```powershell
# Services prüfen:
Get-Service -Name "postgresql*"
# Status sollte "Running" sein

# Falls nicht laufend:
Start-Service -Name "postgresql-x64-15"
```

---

## 🎯 Nächste Schritte

1. ✅ PostgreSQL installiert
2. ✅ Development-DB erstellt
3. ✅ Django migriert
4. → Pipeline-Templates erweitern (3 Typen)
5. → Frontend Quality-Selector bauen

---

## 📚 Nützliche Befehle

```powershell
# PostgreSQL Status:
Get-Service postgresql-x64-15

# PostgreSQL starten:
Start-Service postgresql-x64-15

# PostgreSQL stoppen:
Stop-Service postgresql-x64-15

# DB-Shell (Django):
python manage.py dbshell

# pgAdmin öffnen:
# Start Menu → PostgreSQL 15 → pgAdmin 4

# DB sichern:
pg_dump -U printbuddy_dev printbuddy_dev > backup.sql

# DB wiederherstellen:
psql -U printbuddy_dev printbuddy_dev < backup.sql
```
