#!/usr/bin/env python
"""Check Preview Only PipelineTemplate Configuration."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'printbuddy.settings')
django.setup()

from jobs.models import PipelineTemplate

print("\n=== ALL PIPELINE TEMPLATES ===")
for t in PipelineTemplate.objects.all().order_by('-created_at'):
    print(f"\n{t.name}:")
    print(f"  ID: {t.id}")
    print(f"  is_active: {t.is_active}")
    print(f"  step_generate: {t.step_generate}")
    print(f"  step_upscale: {t.step_upscale}")
    print(f"  step_pod_export: {t.step_pod_export}")
    print(f"  default_model: {t.default_model}")
    print(f"  default_steps: {t.default_steps}")

print("\n=== FILTERED: is_active=True & step_upscale=False ===")
preview_templates = PipelineTemplate.objects.filter(
    is_active=True, 
    step_upscale=False
)
print(f"Count: {preview_templates.count()}")
for t in preview_templates:
    print(f"  - {t.name} (ID: {t.id})")

if preview_templates.count() == 0:
    print("\n⚠️  PROBLEM: Kein 'Preview Only' Template gefunden!")
    print("Studio Job Create wizard kann kein Template finden!\n")
