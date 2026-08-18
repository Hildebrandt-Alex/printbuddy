from jobs.models import Job, JobStep
from django.db.models import Count, Q
from pathlib import Path
import os

# Finde Jobs mit "astronaut" oder mehreren Quick Adjusts
jobs = Job.objects.filter(
    title__icontains='astro'
).order_by('-created_at')[:5]

if not jobs.exists():
    # Falls kein Astronaut, finde Jobs mit mehreren Quick Adjust Steps
    jobs = Job.objects.annotate(
        qa_count=Count('steps', filter=Q(steps__step_type='quick_adjust'))
    ).filter(qa_count__gt=1).order_by('-created_at')[:5]

print(f"=== Found {jobs.count()} Jobs ===\n")

for job in jobs:
    print(f"Job: {job.title}")
    print(f"ID: {job.id}")
    print(f"Status: {job.status}")
    
    # Alle Quick Adjust Steps für diesen Job
    qa_steps = job.steps.filter(step_type='quick_adjust').order_by('-id')
    print(f"Quick Adjust Steps: {qa_steps.count()}")
    
    for i, step in enumerate(qa_steps, 1):
        print(f"\n  QA #{i}:")
        print(f"    Step ID: {step.id}")
        print(f"    Status: {step.status}")
        print(f"    Output Asset ID: {step.output_asset_id}")
        print(f"    Started: {step.started_at}")
        print(f"    Completed: {step.completed_at}")
        
        if step.output_asset_id:
            asset_id = str(step.output_asset_id)
            # Check if file exists
            timestamp = step.completed_at.strftime("%Y%m%d_%H%M%S") if step.completed_at else "unknown"
            filename_new = f"{asset_id}_adjusted_{timestamp}.png"
            filepath_new = Path("/mnt/agency_nas/raw") / filename_new
            
            filename_old = f"{asset_id}_adjusted.png"
            filepath_old = Path("/mnt/agency_nas/raw") / filename_old
            
            print(f"    File (new): {filepath_new.exists()} - {filename_new}")
            print(f"    File (old): {filepath_old.exists()} - {filename_old}")
            
            # Liste alle Dateien mit dieser Asset-ID
            try:
                raw_files = [f for f in os.listdir("/mnt/agency_nas/raw") if asset_id[:8] in f]
                if raw_files:
                    print(f"    NAS Files: {', '.join(raw_files)}")
            except Exception as e:
                print(f"    Error listing files: {e}")
        else:
            print(f"    ❌ Kein output_asset_id - Step wurde nie aktualisiert!")
            if step.error_msg:
                print(f"    Error: {step.error_msg[:100]}")
    
    print("\n" + "="*60 + "\n")
