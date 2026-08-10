#!/usr/bin/env python
"""
Utility Script: Cancel stuck Enhancement jobs.
Verwendung: python manage.py shell < cancel_stuck_jobs.py
"""

from jobs.models import Job, JobStep

# Finde Enhancement-Jobs in Warteschlange
stuck_jobs = Job.objects.filter(
    pipeline_template__step_generate=False,  # Enhancement = kein generate
    status__in=['queued', 'running']
).order_by('-created_at')

print(f"\n=== Gefundene Enhancement Jobs in Queue: {stuck_jobs.count()} ===\n")

for job in stuck_jobs:
    print(f"Job {job.id}:")
    print(f"  Title: {job.title}")
    print(f"  Status: {job.status}")
    print(f"  Created: {job.created_at}")
    
    # Zeige fehlgeschlagene Steps
    failed_steps = job.steps.filter(status='failed')
    for step in failed_steps:
        print(f"  Failed Step: {step.step_type} - {step.error_msg[:80]}")
    
    # Cancel den Job
    job.status = 'cancelled'
    job.save(update_fields=['status'])
    print(f"  ✅ Cancelled\n")

print(f"\n✅ {stuck_jobs.count()} Jobs cancelled.")
