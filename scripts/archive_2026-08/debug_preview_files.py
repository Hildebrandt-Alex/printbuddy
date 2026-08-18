from jobs.models import Job, JobStep
from pathlib import Path
import os

job_id = 'd0763876-801e-4acb-9189-8e5f87454957'
job = Job.objects.get(id=job_id)

print(f"=== Job: {job.title} ===")
print(f"Status: {job.status}")
print(f"Template: {job.pipeline_template.name}")
print()

preview_steps = job.steps.filter(
    step_type__in=["preview_export", "quick_adjust", "crop"],
    status__in=["pending", "running", "done"]
).order_by('-id')

print(f"=== Preview Steps ({preview_steps.count()}) ===")
for step in preview_steps:
    print(f"\nStep ID: {step.id}")
    print(f"  Type: {step.step_type}")
    print(f"  Status: {step.status}")
    print(f"  Output Asset ID: {step.output_asset_id}")
    print(f"  Completed: {step.completed_at}")
    
    if step.output_asset_id:
        asset_id = str(step.output_asset_id)
        
        # Prüfe Preview-Datei
        preview_filename = f"{asset_id}_preview.jpg"
        preview_path = Path("/mnt/agency_nas/exports/preview") / preview_filename
        
        print(f"  Preview Path: {preview_path}")
        print(f"  Preview Exists: {preview_path.exists()}")
        
        # Prüfe Raw-Datei
        raw_filename = f"{asset_id}.png"
        raw_path = Path("/mnt/agency_nas/raw") / raw_filename
        print(f"  Raw Path: {raw_path}")
        print(f"  Raw Exists: {raw_path.exists()}")
        
        # Liste alle Dateien mit diesem Asset-ID
        print(f"\n  Dateien auf NAS mit Asset-ID {asset_id[:8]}:")
        for dir_name, dir_path in [("preview", "/mnt/agency_nas/exports/preview"), 
                                     ("raw", "/mnt/agency_nas/raw")]:
            if Path(dir_path).exists():
                try:
                    files = [f for f in os.listdir(dir_path) if asset_id[:8] in f]
                    if files:
                        for f in files:
                            print(f"    {dir_name}/{f}")
                    else:
                        print(f"    {dir_name}/: keine Dateien")
                except Exception as e:
                    print(f"    {dir_name}/: Error - {e}")

print("\n=== NAS Mount Status ===")
nas_base = Path("/mnt/agency_nas")
print(f"NAS Base exists: {nas_base.exists()}")
if nas_base.exists():
    print(f"exports/preview exists: {(nas_base / 'exports' / 'preview').exists()}")
    print(f"raw exists: {(nas_base / 'raw').exists()}")
