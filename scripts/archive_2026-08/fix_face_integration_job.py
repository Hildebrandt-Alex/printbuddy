from jobs.models import Job, JobStep
from django.utils import timezone
from pathlib import Path

job_id = 'd0763876-801e-4acb-9189-8e5f87454957'
job = Job.objects.get(id=job_id)

print(f"=== Fixing Job: {job.title} ===")

# Finde den Preview-Export Step (status=pending, output_asset_id=None)
preview_step = job.steps.filter(
    step_type='preview_export',
    status='pending'
).first()

if not preview_step:
    print("❌ Kein pending preview_export Step gefunden")
    exit()

print(f"Step ID: {preview_step.id}")
print(f"Current Status: {preview_step.status}")
print(f"Current Asset ID: {preview_step.output_asset_id}")

# Die real existierende Preview-Datei aus den Logs:
asset_id = 'df21033e-9052-4deb-87db-94e16b0300df'
preview_filename = f"{asset_id}_preview.jpg"
preview_path = Path("/mnt/agency_nas/exports/preview") / preview_filename

print(f"\nPreview File: {preview_filename}")
print(f"Path: {preview_path}")
print(f"Exists: {preview_path.exists()}")

if preview_path.exists():
    # Update den JobStep
    preview_step.output_asset_id = asset_id
    preview_step.status = 'done'
    preview_step.started_at = job.started_at or timezone.now()
    preview_step.completed_at = job.completed_at or timezone.now()
    preview_step.save(update_fields=['output_asset_id', 'status', 'started_at', 'completed_at'])
    
    print(f"\n✅ JobStep aktualisiert:")
    print(f"   output_asset_id: {preview_step.output_asset_id}")
    print(f"   status: {preview_step.status}")
    print(f"   completed_at: {preview_step.completed_at}")
else:
    print("\n❌ Preview-Datei existiert nicht auf NAS")
    print("   Job kann nicht gefixt werden")
