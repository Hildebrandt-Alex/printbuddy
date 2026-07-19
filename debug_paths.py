#!/usr/bin/env python
"""Debug-Skript um Bildpfade zu prüfen"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'printbuddy.settings')
django.setup()

from gallery.models import GalleryImage
from jobs.models import Job

print("\n=== GALLERY IMAGES (is_public=True) ===")
for img in GalleryImage.objects.filter(is_public=True)[:5]:
    print(f"\nTitel: {img.title}")
    print(f"  file_path.name: {img.file_path.name}")
    print(f"  thumb_path.name: {img.thumb_path.name if img.thumb_path else 'None'}")
    print(f"  'exports/' in path: {'exports/' in img.file_path.name}")

print("\n\n=== RECENT JOBS (last 3) ===")
for job in Job.objects.order_by('-created_at')[:3]:
    print(f"\nJob: {job.title} (Status: {job.status})")
    print(f"  Model: {job.model}")
    preview_steps = job.steps.filter(step_type='preview_export', status='done')
    for step in preview_steps:
        if step.output_asset_id:
            print(f"  Asset: {step.output_asset_id}_preview.jpg")
