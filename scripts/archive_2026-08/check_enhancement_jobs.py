#!/usr/bin/env python
"""
Check all Enhancement jobs in the database.
"""
from jobs.models import Job

# Find all jobs with Enhancement templates (step_generate=False)
jobs = Job.objects.filter(
    pipeline_template__step_generate=False
).order_by('-created_at')[:15]

print(f"\n=== Enhancement Jobs (Last 15): {jobs.count()} ===\n")

for job in jobs:
    print(f"Job {job.id}")
    print(f"  Title: {job.title}")
    print(f"  Status: {job.status}")
    print(f"  Template: {job.pipeline_template.name}")
    print(f"  Created: {job.created_at}")
    print(f"  Started: {job.started_at}")
    
    # Check steps
    steps = job.steps.all()
    print(f"  Steps: {steps.count()}")
    for step in steps:
        print(f"    - {step.step_type}: {step.status}")
    print()
