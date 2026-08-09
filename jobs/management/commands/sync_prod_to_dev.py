"""
Management Command: Synchronisiert Production-Datenbank nach Development.

WARNUNG: Überschreibt lokale Development-Datenbank komplett!

Usage:
    python manage.py sync_prod_to_dev [--confirm]
    
Dieser Command:
1. Erstellt Backup der lokalen DB (falls vorhanden)
2. Lädt Production DB-Dump herunter via SSH
3. Importiert in lokale SQLite DB

VORAUSSETZUNGEN:
- SSH-Config 'datemyhobby' muss existieren
- Production PostgreSQL muss erreichbar sein
- Genug Speicherplatz für DB-Dump

SICHERHEIT:
- Nur in Development-Umgebung nutzen (DEBUG=True check)
- Erstellt automatisch Backup vor Import
- Interaktive Bestätigung erforderlich
"""

import os
import shutil
import subprocess
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = "Synchronisiert Production-Datenbank nach Development (SQLite)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Bestätigt direkt ohne Nachfrage",
        )
        parser.add_argument(
            "--skip-backup",
            action="store_true",
            help="Überspringt Backup der lokalen DB",
        )

    def handle(self, *args, **options):
        # SICHERHEITSCHECK: Nur in Development erlaubt
        if not settings.DEBUG:
            raise CommandError(
                "❌ Dieser Command darf NUR in Development (DEBUG=True) ausgeführt werden!"
            )

        self.stdout.write(self.style.WARNING("=" * 70))
        self.stdout.write(
            self.style.WARNING("WARNUNG: Production-Datenbank -> Development Sync")
        )
        self.stdout.write(self.style.WARNING("=" * 70))

        self.stdout.write("\nDieser Command wird:")
        self.stdout.write("  1. Production DB-Dump von VPS herunterladen")
        self.stdout.write("  2. In JSON konvertieren")
        self.stdout.write("  3. Lokale SQLite DB überschreiben")
        self.stdout.write(
            "\n⚠️  ALLE lokalen Development-Daten gehen verloren!\n"
        )

        if not options["confirm"]:
            confirm = input("Fortfahren? [ja/NEIN]: ").strip().lower()
            if confirm != "ja":
                self.stdout.write(self.style.ERROR("Abgebrochen."))
                return

        self.stdout.write("\n" + "─" * 70)

        # Pfade
        base_dir = Path(settings.BASE_DIR)
        db_file = base_dir / "db.sqlite3"
        backup_dir = base_dir / "backups"
        backup_dir.mkdir(exist_ok=True)

        # Schritt 1: Lokales Backup (falls vorhanden)
        if db_file.exists() and not options["skip_backup"]:
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f"db_backup_{timestamp}.sqlite3"

            self.stdout.write(f"\n📦 Erstelle Backup: {backup_file.name}")
            shutil.copy2(db_file, backup_file)
            self.stdout.write(
                self.style.SUCCESS(f"   ✅ Backup erstellt")
            )

        # Schritt 2: Production Dump herunterladen
        self.stdout.write("\n🔄 Lade Production-Datenbank...")

        dump_file = backup_dir / "prod_dump.json"

        # SSH Command: Django dumpdata auf Production ausführen
        ssh_command = [
            "ssh",
            "datemyhobby",
            "cd /opt/printbuddy && source venv/bin/activate && python manage.py dumpdata --natural-foreign --natural-primary --indent 2",
        ]

        try:
            result = subprocess.run(
                ssh_command,
                capture_output=True,
                text=True,
                check=True,
                timeout=300,  # 5 Minuten Timeout
            )

            # Dump in Datei speichern
            dump_file.write_text(result.stdout, encoding="utf-8")

            self.stdout.write(
                self.style.SUCCESS(
                    f"   ✅ Production Dump heruntergeladen ({len(result.stdout)} bytes)"
                )
            )

        except subprocess.TimeoutExpired:
            raise CommandError(
                "❌ Timeout beim Production-Dump (>5 Min). Netzwerk prüfen!"
            )
        except subprocess.CalledProcessError as e:
            raise CommandError(
                f"❌ SSH-Fehler beim Production-Dump:\n{e.stderr}"
            )
        except Exception as e:
            raise CommandError(f"❌ Fehler beim Herunterladen: {e}")

        # Schritt 3: Lokale DB löschen
        if db_file.exists():
            self.stdout.write("\n🗑️  Lösche lokale Development-DB...")
            db_file.unlink()
            self.stdout.write(self.style.SUCCESS("   ✅ Alte DB gelöscht"))

        # Schritt 4: Neue DB erstellen (Migrations ausführen)
        self.stdout.write("\n🔧 Erstelle neue SQLite DB (migrate)...")

        try:
            subprocess.run(
                ["python", "manage.py", "migrate", "--run-syncdb"],
                check=True,
                capture_output=True,
                text=True,
            )
            self.stdout.write(self.style.SUCCESS("   ✅ Migrations angewendet"))
        except subprocess.CalledProcessError as e:
            raise CommandError(f"❌ Migration fehlgeschlagen:\n{e.stderr}")

        # Schritt 5: Production-Daten importieren
        self.stdout.write("\n📥 Importiere Production-Daten...")

        try:
            result = subprocess.run(
                ["python", "manage.py", "loaddata", str(dump_file)],
                check=True,
                capture_output=True,
                text=True,
            )
            self.stdout.write(
                self.style.SUCCESS("   ✅ Production-Daten importiert")
            )

            # Zeige Import-Statistik
            lines = result.stdout.strip().split("\n")
            for line in lines:
                if "Installed" in line or "objects" in line:
                    self.stdout.write(f"      {line}")

        except subprocess.CalledProcessError as e:
            raise CommandError(f"❌ Import fehlgeschlagen:\n{e.stderr}")

        # Schritt 6: Cleanup
        self.stdout.write("\n🧹 Cleanup...")
        dump_file.unlink()
        self.stdout.write(self.style.SUCCESS("   ✅ Temp-Dateien entfernt"))

        # Zusammenfassung
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(
            self.style.SUCCESS("✅ ERFOLG: Development DB mit Production synchronisiert!")
        )
        self.stdout.write("=" * 70)

        # Datenbankstatistik
        self.stdout.write("\n📊 Datenbank-Statistik:\n")

        try:
            with connection.cursor() as cursor:
                # SQLite: Alle Tabellen und Row-Counts
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
                )
                tables = cursor.fetchall()

                for (table_name,) in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    if count > 0:
                        self.stdout.write(f"   {table_name:30s}: {count:5d} rows")

        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"   ⚠️  Statistik-Fehler: {e}")
            )

        # Hinweise
        self.stdout.write("\n" + "─" * 70)
        self.stdout.write("💡 Nächste Schritte:")
        self.stdout.write("   1. Superuser erstellen: python manage.py createsuperuser")
        self.stdout.write(
            "   2. Media-Files synchronisieren (optional): rsync -avz datemyhobby:/mnt/agency_nas/ local_nas/"
        )
        self.stdout.write("   3. Development-Server starten: python manage.py runserver")
        self.stdout.write("\n")
