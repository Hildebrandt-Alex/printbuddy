from jobs.models import Job, JobStep
from pathlib import Path
import os
import re

print("=== Workflow-Analyse: Quick Adjust -> Enhancement ===\n")

# Für test22: Zeige kompletten Asset-Flow
job = Job.objects.get(title='test22')

print(f"Job: {job.title}")
print(f"Status: {job.status}")
print(f"Created: {job.created_at}\n")

# 1. Original Generation
generate_step = job.steps.filter(step_type='generate').first()
if generate_step:
    print(f"1️⃣ GENERATE")
    print(f"   Asset ID: {generate_step.output_asset_id}")
    print(f"   Status: {generate_step.status}\n")
    
    orig_asset = str(generate_step.output_asset_id)
    
    # Prüfe Datei
    raw_file = Path(f"/mnt/agency_nas/raw/{orig_asset}.png")
    print(f"   Datei: {raw_file.name}")
    print(f"   Exists: {raw_file.exists()}\n")

# 2. Preview Export
preview_step = job.steps.filter(step_type='preview_export').first()
if preview_step:
    print(f"2️⃣ PREVIEW EXPORT")
    print(f"   Asset ID: {preview_step.output_asset_id}")
    print(f"   Status: {preview_step.status}\n")
    
    preview_asset = str(preview_step.output_asset_id)
    
    # Prüfe Datei
    preview_file = Path(f"/mnt/agency_nas/exports/preview/{preview_asset}_preview.jpg")
    print(f"   Datei: {preview_file.name}")
    print(f"   Exists: {preview_file.exists()}\n")

# 3. Quick Adjusts (nur die mit Assets)
qa_steps = job.steps.filter(
    step_type='quick_adjust',
    output_asset_id__isnull=False
).order_by('order')

print(f"3️⃣ QUICK ADJUSTS ({qa_steps.count()} mit Assets)")
for i, step in enumerate(qa_steps, 1):
    qa_asset = str(step.output_asset_id)
    print(f"\n   QA #{i} (Order {step.order})")
    print(f"   Asset ID: {qa_asset}")
    print(f"   Completed: {step.completed_at}")
    
    # Suche Datei auf NAS
    raw_dir = "/mnt/agency_nas/raw"
    pattern = f"{qa_asset}_adjusted"
    files = [f for f in os.listdir(raw_dir) if pattern in f]
    
    if files:
        print(f"   ✅ Datei: {files[0]}")
    else:
        print(f"   ❌ Keine Datei gefunden (Pattern: {pattern})")

# 4. Workflow-Logik Analyse
print(f"\n\n{'='*60}")
print(f"WORKFLOW-LOGIK PRÜFUNG\n")

print("✅ KORREKT:")
print("   1. Job erstellen -> Generate -> Preview Export")
print("   2. User sieht Preview in job_results View")
print("   3. User klickt 'Quick Adjust' Button")
print("   4. Neuer JobStep (quick_adjust) wird erstellt mit status='pending'")
print("   5. Celery Task erstellt adjusted Datei mit neuer UUID")
print("   6. _save_step aktualisiert JobStep mit output_asset_id")
print("   7. User sieht adjusted Bild in job_results View")
print("   8. User wählt adjusted Bild -> Enhancement Job")

print("\n❌ PROBLEM IN AKTUELLER IMPLEMENTIERUNG:")
print("   - JobStep hat KEINE Referenz zum source_asset_id")
print("   - Kein Feld für 'welches Bild wurde adjusted?'")
print("   - Enhancement-Job braucht aber source_asset_id!")

print("\n🔧 BENÖTIGTE ÄNDERUNGEN:")
print("   1. JobStep.source_asset_id Feld hinzufügen (Migration)")
print("   2. Quick Adjust Tasks müssen source speichern")
print("   3. Enhancement-Job Erstellung braucht source_asset_id im notes JSON")

# Prüfe: Haben die QA Steps notes mit source info?
print(f"\n{'='*60}")
print("PRÜFUNG: Haben Quick Adjust Steps source_asset Info?\n")

for step in qa_steps:
    print(f"Step {str(step.id)[:8]}: {step.params}")
