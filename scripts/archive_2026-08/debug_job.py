#!/usr/bin/env python
"""Debug Job Results Error"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'printbuddy.settings')
django.setup()

from jobs.models import Job, JobStep

job_id = 'd0763876-801e-4acb-9189-8e5f87454957'

try:
    job = Job.objects.get(id=job_id)
    print(f'Job gefunden: {job.title}')
    print(f'Status: {job.status}')
    print(f'User: {job.created_by.username}')
    print(f'Pipeline Template: {job.pipeline_template}')
    print(f'Model: {job.model}')
    print()
    
    # Steps ausgeben
    steps = job.steps.filter(
        step_type__in=['preview_export', 'quick_adjust', 'crop'],
        status__in=['pending', 'running', 'done']
    ).order_by('-created_at')
    
    print(f'Gefundene Steps: {steps.count()}')
    for s in steps:
        print(f'  {s.step_type}: {s.status}, output_asset_id={s.output_asset_id}, completed_at={s.completed_at}')
        
    print()
    print('--- Testing job_results View Logic ---')
    
    # Simulate View Logic
    from pathlib import Path
    from django.conf import settings
    
    preview_dir = Path(getattr(settings, "NAS_BASE_PATH", "local_nas")) / "exports" / "preview"
    raw_dir = Path(getattr(settings, "NAS_BASE_PATH", "local_nas")) / "raw"
    
    print(f'Preview dir: {preview_dir}')
    print(f'Raw dir: {raw_dir}')
    
    assets = []
    for step in steps:
        if not step.output_asset_id:
            print(f'  Step {step.step_type} has no output_asset_id (status={step.status})')
            continue
        
        asset_id = str(step.output_asset_id)
        print(f'  Processing asset_id: {asset_id} (step_type={step.step_type})')
        
        if step.step_type == "quick_adjust":
            if step.completed_at:
                timestamp = step.completed_at.strftime("%Y%m%d_%H%M%S")
                print(f'    Timestamp: {timestamp}')
            else:
                print(f'    ERROR: step.completed_at is None for done step!')
                
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
