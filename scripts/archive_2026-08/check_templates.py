#!/usr/bin/env python
"""
Check PipelineTemplates in the database.
"""
from jobs.models import PipelineTemplate, Job

print("\n=== Pipeline Templates ===\n")
templates = PipelineTemplate.objects.all().order_by('name')

for t in templates:
    print(f"{t.name}")
    print(f"  ID: {t.id}")
    print(f"  step_generate: {t.step_generate}")
    print(f"  step_upscale: {t.step_upscale}")
    print(f"  is_active: {t.is_active}")
    
    # Count jobs with this template
    jobs_count = Job.objects.filter(pipeline_template=t).count()
    print(f"  Jobs: {jobs_count}")
    
    # Last 3 jobs
    recent_jobs = Job.objects.filter(pipeline_template=t).order_by('-created_at')[:3]
    if recent_jobs:
        print(f"  Recent Jobs:")
        for j in recent_jobs:
            print(f"    - {j.title[:50]} | Status: {j.status} | Created: {j.created_at}")
    print()
