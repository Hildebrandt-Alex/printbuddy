# Generated manually on 2026-08-05
# Fixiert MASSIVE Schema-Desync zwischen Model und Production DB
# HINWEIS: Wurde bereits manuell per SQL ausgeführt am 05.08.2026 23:35 UTC

from django.db import migrations


def fix_schema_postgresql_only(apps, schema_editor):
    """
    Fixe Schema nur auf PostgreSQL, SQLite überspringen.
    """
    if schema_editor.connection.vendor != 'postgresql':
        return  # SQLite hat sauberes Schema, nichts zu tun
    
    with schema_editor.connection.cursor() as cursor:
        # Entferne orphan fields (nicht im Model)
        cursor.execute("""
            DO $$ 
            BEGIN
                -- Entferne reference_images (plural, orphan field)
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='jobs_job' AND column_name='reference_images'
                ) THEN
                    ALTER TABLE jobs_job DROP COLUMN reference_images;
                END IF;
                
                -- Entferne source_asset_id (orphan field)
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='jobs_job' AND column_name='source_asset_id'
                ) THEN
                    ALTER TABLE jobs_job DROP COLUMN source_asset_id;
                END IF;
            END $$;
        """)
        
        # Fixe NOT NULL Constraints (Model hat blank=True)
        cursor.execute("""
            DO $$
            BEGIN
                -- reference_image: ImageField(blank=True) -> NULL erlauben
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='jobs_job' AND column_name='reference_image' AND is_nullable='NO'
                ) THEN
                    ALTER TABLE jobs_job ALTER COLUMN reference_image DROP NOT NULL;
                END IF;
                
                -- face_image: ImageField(blank=True) -> NULL erlauben
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='jobs_job' AND column_name='face_image' AND is_nullable='NO'
                ) THEN
                    ALTER TABLE jobs_job ALTER COLUMN face_image DROP NOT NULL;
                END IF;
                
                -- negative_prompt: TextField(blank=True) -> NULL erlauben
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='jobs_job' AND column_name='negative_prompt' AND is_nullable='NO'
                ) THEN
                    ALTER TABLE jobs_job ALTER COLUMN negative_prompt DROP NOT NULL;
                END IF;
                
                -- model: CharField(blank=True) -> NULL erlauben
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='jobs_job' AND column_name='model' AND is_nullable='NO'
                ) THEN
                    ALTER TABLE jobs_job ALTER COLUMN model DROP NOT NULL;
                END IF;
                
                -- celery_chain_id: CharField(blank=True) -> NULL erlauben
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='jobs_job' AND column_name='celery_chain_id' AND is_nullable='NO'
                ) THEN
                    ALTER TABLE jobs_job ALTER COLUMN celery_chain_id DROP NOT NULL;
                END IF;
                
                -- notes: TextField(blank=True) -> NULL erlauben
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='jobs_job' AND column_name='notes' AND is_nullable='NO'
                ) THEN
                    ALTER TABLE jobs_job ALTER COLUMN notes DROP NOT NULL;
                END IF;
            END $$;
        """)


class Migration(migrations.Migration):
    """
    Behebt massives Schema-Desync Problem in Production PostgreSQL.
    
    PROBLEME:
    1. Orphan fields: reference_images, source_asset_id (nicht im Model)
    2. Falsche NOT NULL constraints auf blank=True Feldern
    
    LÖSUNG:
    - DROP orphan fields
    - ALTER COLUMN ... DROP NOT NULL für alle blank=True Felder
    
    Diese Migration ist idempotent (wiederholbar ohne Fehler).
    Läuft NUR auf PostgreSQL, SQLite wird übersprungen.
    """

    dependencies = [
        ("jobs", "0008_remove_pipeline_params"),
    ]

    operations = [
        migrations.RunPython(
            code=fix_schema_postgresql_only,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
