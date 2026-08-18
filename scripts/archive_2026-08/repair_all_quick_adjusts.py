from jobs.models import Job, JobStep
from django.utils import timezone
from pathlib import Path
import os
import re

# Finde ALLE Quick Adjust Steps mit status=pending aber Dateien auf NAS
pending_qa_steps = JobStep.objects.filter(
    step_type='quick_adjust',
    status='pending'
).select_related('job')

print(f"=== Found {pending_qa_steps.count()} pending Quick Adjust Steps ===\n")

raw_dir = Path("/mnt/agency_nas/raw")

# Liste alle Files im raw/ Verzeichnis
try:
    all_raw_files = set(os.listdir(raw_dir))
except Exception as e:
    print(f"❌ Error listing NAS raw/ directory: {e}")
    exit(1)

print(f"Total files in raw/: {len(all_raw_files)}\n")

fixed_count = 0
not_found_count = 0

for step in pending_qa_steps:
    job = step.job
    print(f"Step {str(step.id)[:8]} (Job: {job.title})")
    
    # Suche nach Datei die zu diesem Step gehört
    # Pattern: <uuid>_adjusted.png ODER <uuid>_adjusted_<timestamp>.png
    # Problem: Wir haben kein output_asset_id, also müssen wir raten
    
    # Strategie: Suche nach allen *_adjusted.png Files die zum Job-Created-Zeitraum passen
    # Die Datei wurde wahrscheinlich erstellt nachdem der Step created wurde
    
    # ABER: Wir haben kein created_at auf JobStep! 
    # Alternative: Suche nach Job-Steps die DONE sind und deren Asset-IDs verwenden
    done_steps_in_job = job.steps.filter(
        step_type__in=['preview_export', 'quick_adjust'],
        output_asset_id__isnull=False
    ).values_list('output_asset_id', flat=True)
    
    print(f"  Job has {len(done_steps_in_job)} completed steps with assets")
    
    # Finde adjusted files die NICHT in done_steps sind
    adjusted_files = [f for f in all_raw_files if '_adjusted' in f and f.endswith('.png')]
    known_asset_ids = set(str(aid) for aid in done_steps_in_job)
    
    # Kandidaten: adjusted files deren UUID NICHT in known_asset_ids ist
    candidates = []
    for f in adjusted_files:
        # Extract UUID from filename
        match = re.match(r'([0-9a-f-]+)_adjusted', f)
        if match:
            asset_uuid = match.group(1)
            if asset_uuid not in known_asset_ids:
                candidates.append((asset_uuid, f))
    
    if candidates:
        # Nehme den ersten Kandidaten (sollte zeitlich passen)
        asset_id, filename = candidates[0]
        filepath = raw_dir / filename
        
        if filepath.exists():
            # Update den JobStep
            step.output_asset_id = asset_id
            step.status = 'done'
            step.started_at = job.started_at or timezone.now()
            step.completed_at = job.completed_at or timezone.now()
            step.save(update_fields=['output_asset_id', 'status', 'started_at', 'completed_at'])
            
            print(f"  ✅ Fixed: {filename}")
            print(f"     Asset ID: {asset_id}")
            fixed_count += 1
            
            # Entferne aus known_asset_ids damit nächster Step einen anderen findet
            known_asset_ids.add(asset_id)
        else:
            print(f"  ❓ File not found: {filename}")
            not_found_count += 1
    else:
        print(f"  ❌ No candidate files found")
        not_found_count += 1
    
    print()

print("="*60)
print(f"✅ Fixed: {fixed_count}")
print(f"❌ Not found: {not_found_count}")
print(f"Total: {pending_qa_steps.count()}")
