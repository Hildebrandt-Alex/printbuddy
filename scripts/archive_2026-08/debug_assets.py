#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "printbuddy.settings.production")
sys.path.append("/opt/printbuddy")
django.setup()

from jobs.models import JobStep

print("=== Last 5 Quick Adjust Steps ===")
steps = JobStep.objects.filter(step_type="quick_adjust").order_by("-completed_at")[:5]
for s in steps:
    print(f"Job: {s.job_id}")
    print(f"  Status: {s.status}")
    print(f"  Output Asset ID: {s.output_asset_id}")
    print(f"  Expected Filename: {s.output_asset_id}_adjusted.png")
    print(f"  Created: {s.completed_at}")
    print()
