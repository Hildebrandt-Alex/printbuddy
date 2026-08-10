#!/usr/bin/env python
"""
Check all recent jobs and their steps.
"""
from jobs.models import Job, JobStep
from datetime import datetime, timedelta

print("\n=== Alle Jobs der letzten 24 Stunden ===\n")

yesterday = datetime.now() - timedelta(days=1)
recent_jobs = Job.objects.filter(created_at__gte=yesterday).order_by('-created_at')

print(f"Total: {recent_jobs.count()}\n")

for job in recent_jobs:
    print(f"Job {job.id}")
    print(f"  Title: {job.title[:60]}")
    print(f"  Status: {job.status}")
    print(f"  Template: {job.pipeline_template.name}")
    print(f"  Created: {job.created_at}")
    
    # Get ALL steps
    steps = job.steps.all().order_by('order', '-created_at')
    print(f"  Steps ({steps.count()}):")
    
    for step in steps:
        print(f"    {step.step_type}: {step.status} | Asset: {step.output_asset_id or 'None'}")
        if step.error_msg:
            print(f"      ERROR: {step.error_msg[:100]}")
    
    # Check notes for source_asset_id
    if job.notes:
        import json
        try:
            notes = json.loads(job.notes)
            if 'source_asset_id' in notes:
                print(f"  Source Asset: {notes['source_asset_id']}")
            if 'quick_adjust_params' in notes:
                print(f"  Quick Adjust Params: {notes['quick_adjust_params']}")
        except:
            pass
    
    print()
