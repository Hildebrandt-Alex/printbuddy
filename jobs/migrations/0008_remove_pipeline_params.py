# Generated manually on 2026-08-05
# Entfernt orphan field 'pipeline_params' aus Production DB
# HINWEIS: Wurde manuell per SQL ausgeführt am 05.08.2026 23:30 UTC
# sudo -u postgres psql -d printbuddy -c 'ALTER TABLE jobs_job DROP COLUMN pipeline_params;'

from django.db import migrations


class Migration(migrations.Migration):
    """
    Diese Migration entfernt das orphan field 'pipeline_params' aus PostgreSQL.
    Das Feld existierte in Production DB aber nicht mehr im Model.
    
    WICHTIG: Wurde bereits manuell ausgeführt via SQL, daher ist diese Migration
    idempotent (wiederholbar ohne Fehler).
    """

    dependencies = [
        ("jobs", "0007_add_face_image"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                DO $$ 
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name='jobs_job' AND column_name='pipeline_params'
                    ) THEN
                        ALTER TABLE jobs_job DROP COLUMN pipeline_params;
                    END IF;
                END $$;
            """,
            reverse_sql=migrations.RunSQL.noop,
            state_operations=[],  # Kein Model-State-Change nötig
        ),
    ]
