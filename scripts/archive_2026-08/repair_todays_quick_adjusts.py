from jobs.models import Job, JobStep
from django.utils import timezone
from pathlib import Path

print("=== Repair hängende Quick Adjust Steps ===\n")

# face integration: 075c494b-9b14-44d3-8e62-bd648e4b303f
job1 = Job.objects.get(title='face integration')
step1 = job1.steps.filter(step_type='quick_adjust', status='pending').first()

if step1:
    asset_id1 = '075c494b-9b14-44d3-8e62-bd648e4b303f'
    file1 = Path(f"/mnt/agency_nas/raw/{asset_id1}_adjusted_20260817_145434.png")
    
    if file1.exists():
        step1.output_asset_id = asset_id1
        step1.status = 'done'
        step1.started_at = timezone.datetime(2026, 8, 17, 14, 54, 34, tzinfo=timezone.get_current_timezone())
        step1.completed_at = timezone.datetime(2026, 8, 17, 14, 54, 36, tzinfo=timezone.get_current_timezone())
        step1.save(update_fields=['output_asset_id', 'status', 'started_at', 'completed_at'])
        print(f"✅ face integration: Step {str(step1.id)[:8]} -> {asset_id1}")
        print(f"   Datei: {file1.name}\n")
    else:
        print(f"❌ face integration: Datei nicht gefunden: {file1}\n")
else:
    print("⚠️ face integration: Kein pending Quick Adjust Step\n")

# sdxl: 47a23dad-dfbf-4909-a3e0-c7e36eee6589
job2 = Job.objects.get(title='sdxl')
step2 = job2.steps.filter(step_type='quick_adjust', status='pending').first()

if step2:
    asset_id2 = '47a23dad-dfbf-4909-a3e0-c7e36eee6589'
    file2 = Path(f"/mnt/agency_nas/raw/{asset_id2}_adjusted_20260817_145829.png")
    
    if file2.exists():
        step2.output_asset_id = asset_id2
        step2.status = 'done'
        step2.started_at = timezone.datetime(2026, 8, 17, 14, 58, 29, tzinfo=timezone.get_current_timezone())
        step2.completed_at = timezone.datetime(2026, 8, 17, 14, 58, 31, tzinfo=timezone.get_current_timezone())
        step2.save(update_fields=['output_asset_id', 'status', 'started_at', 'completed_at'])
        print(f"✅ sdxl: Step {str(step2.id)[:8]} -> {asset_id2}")
        print(f"   Datei: {file2.name}\n")
    else:
        print(f"❌ sdxl: Datei nicht gefunden: {file2}\n")
else:
    print("⚠️ sdxl: Kein pending Quick Adjust Step\n")

print("=== Abgeschlossen ===")
