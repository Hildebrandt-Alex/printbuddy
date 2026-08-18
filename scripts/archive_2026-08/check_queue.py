#!/usr/bin/env python
"""
Check all jobs in queued/running status.
"""
from jobs.models import Job

print("\n=== Jobs in Queue (queued/running) ===\n")
queued_jobs = Job.objects.filter(status__in=['queued', 'running']).order_by('-created_at')

print(f"Total: {queued_jobs.count()}\n")

for job in queued_jobs:
    print(f"Job {job.id}")
    print(f"  Title: {job.title}")
    print(f"  Status: {job.status}")
    print(f"  Template: {job.pipeline_template.name}")
    print(f"  Created: {job.created_at}")
    print(f"  Started: {job.started_at}")
    
    # Check steps
    steps = job.steps.all().order_by('order')
    print(f"  Steps ({steps.count()}):")
    for step in steps:
        print(f"    {step.order}. {step.step_type}: {step.status}")
        if step.error_msg:
            print(f"       ERROR: {step.error_msg[:100]}")
    print()

print("\n=== Failed Jobs (last 10) ===\n")
failed_jobs = Job.objects.filter(status='failed').order_by('-created_at')[:10]

for job in failed_jobs:
    print(f"Job {job.id}")
    print(f"  Title: {job.title}")
    print(f"  Template: {job.pipeline_template.name}")
    print(f"  Created: {job.created_at}")
    
    # Check for failed steps
    failed_steps = job.steps.filter(status='failed')
    if failed_steps.exists():
        print(f"  Failed Steps:")
        for step in failed_steps:
            print(f"    - {step.step_type}: {step.error_msg[:150]}")
    print()
