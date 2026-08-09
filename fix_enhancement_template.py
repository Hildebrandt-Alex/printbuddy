#!/usr/bin/env python
"""
Fix Enhancement Template: Aktiviere step_vectorize und step_cmyk
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'printbuddy.settings.production')
django.setup()

from jobs.models import PipelineTemplate

# Enhancement Template finden
template = PipelineTemplate.objects.filter(name__icontains="Enhancement").first()

if not template:
    print("❌ Enhancement Template nicht gefunden!")
    print("Verfügbare Templates:")
    for t in PipelineTemplate.objects.all():
        print(f"  - {t.name} (generate={t.step_generate})")
else:
    print(f"✅ Template gefunden: {template.name}")
    print(f"   step_generate: {template.step_generate}")
    print(f"   step_vectorize: {template.step_vectorize} → TRUE")
    print(f"   step_cmyk: {template.step_cmyk} → TRUE")
    
    # Aktivieren
    template.step_vectorize = True
    template.step_cmyk = True
    template.save()
    
    print("✅ Enhancement Template aktualisiert!")
