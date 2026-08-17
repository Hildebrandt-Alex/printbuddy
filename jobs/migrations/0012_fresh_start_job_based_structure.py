# Fresh Start Migration: Job-basierte Ordnerstruktur
# ⚠️  DESTRUCTIVE: Löscht ALLE Jobs, JobSteps und GalleryImages!

from django.db import migrations


def delete_all_data(apps, schema_editor):
    """
    Fresh Start: Löscht alle alten Jobs + Steps + GalleryImages.
    Danach wird neue job-basierte Ordnerstruktur verwendet.
    """
    Job = apps.get_model('jobs', 'Job')
    JobStep = apps.get_model('jobs', 'JobStep')
    GalleryImage = apps.get_model('gallery', 'GalleryImage')
    
    # Reihenfolge wichtig: Steps vor Jobs (FK)
    deleted_steps = JobStep.objects.all().count()
    JobStep.objects.all().delete()
    
    deleted_jobs = Job.objects.all().count()
    Job.objects.all().delete()
    
    deleted_images = GalleryImage.objects.all().count()
    GalleryImage.objects.all().delete()
    
    print(f"🗑️  Fresh Start Cleanup:")
    print(f"   - {deleted_jobs} Jobs gelöscht")
    print(f"   - {deleted_steps} JobSteps gelöscht")
    print(f"   - {deleted_images} GalleryImages gelöscht")
    print(f"✅ Datenbank bereit für job-basierte Struktur")


def reverse_noop(apps, schema_editor):
    """Rollback nicht möglich — Daten sind gelöscht"""
    print("⚠️  WARNUNG: Rollback nicht möglich, Daten wurden gelöscht!")


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0011_add_quick_adjust_crop_steps'),
        ('gallery', '0002_add_project_system'),
    ]

    operations = [
        migrations.RunPython(delete_all_data, reverse_noop),
    ]
