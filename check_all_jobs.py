#!/usr/bin/env python
"""
Check last 10 jobs regardless of date.
"""
from jobs.models import Job, JobStep

print("\n=== Letzte 10 Jobs (egal wann) ===\n")

recent_jobs = Job.objects.all().order_by('-created_at')[:10]

print(f"Total Jobs in DB: {Job.objects.count()}")
print(f"Showing last 10:\n")

for job in recent_jobs:
    print(f"Job {job.id}")
    print(f"  Title: {job.title[:60]}")
    print(f"  Status: {job.status}")
    print(f"  Template: {job.pipeline_template.name}")
    print(f"  Created: {job.created_at}")
    print(f"  Updated: {job.updated_at if hasattr(job, 'updated_at') else 'N/A'}")
    
    # Get ALL steps
    steps = job.steps.all().order_by('order', '-created_at')
    print(f"  Steps ({steps.count()}):")
    
    for step in steps:
        status_icon = "✅" if step.status == "done" else "⏸️" if step.status == "pending" else "🔄" if step.status == "running" else "❌"
        print(f"    {status_icon} {step.step_type}: {step.status}")
        if step.output_asset_id:
            print(f"       Asset: {step.output_asset_id}")
        if step.error_msg:
            print(f"       ERROR: {step.error_msg[:100]}")
    
    # Check notes
    if job.notes:
        import json
        try:
            notes = json.loads(job.notes)
            if 'source_asset_id' in notes:
                print(f"  📎 Source Asset: {notes['source_asset_id']}")
            if 'quick_adjust_params' in notes:
                params = notes['quick_adjust_params']
                print(f"  🎨 Quick Adjust: brightness={params.get('brightness', 0)}, contrast={params.get('contrast', 0)}")
        except:
            pass
    
    print()

print("\n=== Quick Adjust Steps (alle) ===\n")
qa_steps = JobStep.objects.filter(step_type='quick_adjust').order_by('-created_at')[:10]
print(f"Total: {qa_steps.count()}\n")

for step in qa_steps:
    print(f"Step {step.id}")
    print(f"  Job: {step.job.title[:40]}")
    print(f"  Status: {step.status}")
    print(f"  Asset ID: {step.output_asset_id or 'None'}")
    print(f"  Created: {step.created_at}")
    print(f"  Completed: {step.completed_at or 'Not yet'}")
    print()
