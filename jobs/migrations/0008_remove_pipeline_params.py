# Generated manually on 2026-08-05
# Entfernt orphan field 'pipeline_params' aus Production DB
# HINWEIS: Wurde manuell per SQL ausgeführt am 05.08.2026 23:30 UTC
# sudo -u postgres psql -d printbuddy -c 'ALTER TABLE jobs_job DROP COLUMN pipeline_params;'

from django.db import migrations


def remove_pipeline_params_postgresql_only(apps, schema_editor):
    """
    Entferne orphan field nur auf PostgreSQL, SQLite überspringen.
    """
    if schema_editor.connection.vendor != 'postgresql':
        return  # SQLite hat das Feld nie gehabt, nichts zu tun
    
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            DO $$ 
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='jobs_job' AND column_name='pipeline_params'
                ) THEN
                    ALTER TABLE jobs_job DROP COLUMN pipeline_params;
                END IF;
            END $$;
        """)


class Migration(migrations.Migration):
    """
    Diese Migration entfernt das orphan field 'pipeline_params' aus PostgreSQL.
    Das Feld existierte in Production DB aber nicht mehr im Model.
    
    WICHTIG: Wurde bereits manuell ausgeführt via SQL, daher ist diese Migration
    idempotent (wiederholbar ohne Fehler).
    
    Läuft NUR auf PostgreSQL, SQLite wird übersprungen.
    """

    dependencies = [
        ("jobs", "0007_add_face_image"),
    ]

    operations = [
        migrations.RunPython(
            code=remove_pipeline_params_postgresql_only,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
