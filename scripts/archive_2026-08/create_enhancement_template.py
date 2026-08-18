#!/usr/bin/env python
"""
Enhancement Template anlegen — kein Generate, nur Post-Processing
"""
import os
import sys
import django

# Django Setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "printbuddy.settings.production")
sys.path.append("/opt/printbuddy")
django.setup()

from jobs.models import PipelineTemplate

# Prüfen ob schon existiert
existing = PipelineTemplate.objects.filter(name__icontains="Enhancement")
if existing.exists():
    print(f"❌ Enhancement Template existiert bereits: {existing.first().name}")
    sys.exit(1)

# Template anlegen
template = PipelineTemplate.objects.create(
    name="Enhancement — Post-Processing Only",
    description="Nur Post-Processing: Upscale, Vectorize, CMYK, POD Export. Kein Generate.",
    category="custom",
    
    # Pipeline Steps
    step_generate=False,      # ❌ Kein neues Bild!
    step_upscale=True,        # ✅ Hochskalieren auf 4x
    step_vectorize=True,      # ✅ SVG Export
    step_cmyk=True,           # ✅ CMYK TIFF + PDF/X-4
    step_pod_export=True,     # ✅ PNG 300dpi sRGB
    step_preview=True,        # ✅ JPG 72dpi (immer)
    step_mockup=False,        # ❌ Mockup optional später
    step_auto_qa=True,        # ✅ Auto Quality Check
    
    # Default Parameter (werden ignoriert da step_generate=False)
    default_width=1024,
    default_height=1024,
    default_dpi=300,
    default_steps=30,
    default_guidance=7.5,
    default_model="flux_schnell",
    
    is_active=True
)

print("✅ Enhancement Template erfolgreich angelegt!")
print(f"   ID: {template.id}")
print(f"   Name: {template.name}")
print(f"   Category: {template.category}")
print("\nAktivierte Steps:")
print(f"   - Generate: {template.step_generate}")
print(f"   - Upscale: {template.step_upscale}")
print(f"   - Vectorize: {template.step_vectorize}")
print(f"   - CMYK: {template.step_cmyk}")
print(f"   - POD Export: {template.step_pod_export}")
print(f"   - Preview: {template.step_preview}")
print(f"   - Mockup: {template.step_mockup}")
print(f"   - Auto QA: {template.step_auto_qa}")
