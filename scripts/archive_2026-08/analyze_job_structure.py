from jobs.models import Job, JobStep
from pathlib import Path
import os

# Analysiere die Job-Asset-Struktur für test22
job = Job.objects.get(title='test22')

print(f"=== Job: {job.title} ({job.id}) ===\n")

# Hole ALLE Steps (nicht nur Quick Adjust)
all_steps = job.steps.all().order_by('order', '-id')

print("=== Alle Steps des Jobs ===")
for step in all_steps:
    print(f"{step.step_type:20s} | Status: {step.status:10s} | Asset: {step.output_asset_id or 'None'}")

print("\n=== Preview + Quick Adjust Steps ===")
selected_steps = job.steps.filter(
    step_type__in=['preview_export', 'quick_adjust']
).order_by('-id')

for step in selected_steps:
    print(f"\n{step.step_type} (Step {str(step.id)[:8]})")
    print(f"  Status: {step.status}")
    print(f"  Asset ID: {step.output_asset_id}")
    print(f"  Order: {step.order}")
    print(f"  Started: {step.started_at}")
    print(f"  Completed: {step.completed_at}")
    
    if step.output_asset_id:
        asset_id = str(step.output_asset_id)
        # Suche Datei auf NAS
        if step.step_type == 'quick_adjust':
            pattern = f"{asset_id}_adjusted"
            search_dir = "/mnt/agency_nas/raw"
        else:
            pattern = f"{asset_id}_preview"
            search_dir = "/mnt/agency_nas/exports/preview"
        
        try:
            files = [f for f in os.listdir(search_dir) if pattern in f]
            if files:
                print(f"  Files: {', '.join(files)}")
            else:
                print(f"  ❌ Keine Datei gefunden mit Pattern: {pattern}")
        except Exception as e:
            print(f"  Error listing files: {e}")

print("\n\n=== Problem-Analyse ===")
# Finde das ursprüngliche Preview-Asset (generate -> preview_export)
original_preview = job.steps.filter(
    step_type='preview_export',
    output_asset_id__isnull=False
).order_by('id').first()

if original_preview:
    print(f"Original Preview Asset: {original_preview.output_asset_id}")
    print(f"  Datei: {original_preview.output_asset_id}_preview.jpg")
    
    # Quick Adjusts sollten auf DIESEM Asset basieren
    print("\n✅ Korrekte Quick Adjust Logik:")
    print(f"   1. User macht Quick Adjust auf {original_preview.output_asset_id}")
    print(f"   2. System erstellt neue UUID für adjusted Bild")
    print(f"   3. Datei: <neue_uuid>_adjusted.png (basierend auf original preview)")
    print(f"   4. JobStep bekommt diese neue UUID als output_asset_id")
else:
    print("❌ Kein originales Preview gefunden!")
