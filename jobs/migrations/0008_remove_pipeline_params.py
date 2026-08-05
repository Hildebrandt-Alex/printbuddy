# Generated manually on 2026-08-05
# Entfernt orphan field 'pipeline_params' aus Production DB

from django.db import migrations


def remove_pipeline_params(apps, schema_editor):
    """
    Entfernt pipeline_params Spalte falls vorhanden.
    SQLite unterstützt DROP COLUMN nicht - dort ist das Feld eh nicht vorhanden.
    """
    if schema_editor.connection.vendor == 'postgresql':
        with schema_editor.connection.cursor() as cursor:
            cursor.execute("""
                ALTER TABLE jobs_job 
                DROP COLUMN IF EXISTS pipeline_params;
            """)


class Migration(migrations.Migration):

    dependencies = [
        ("jobs", "0007_add_face_image"),
    ]

    operations = [
        migrations.RunPython(
            code=remove_pipeline_params,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
