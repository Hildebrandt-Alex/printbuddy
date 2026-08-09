"""
Management Command: Erstellt Pipeline-Templates für Two-Phase Workflow
- Preview Only: Schnelle Preview ohne Upscale
- Face Swap Preview: Generate → Face Swap → Preview
"""
from django.core.management.base import BaseCommand
from jobs.models import PipelineTemplate


class Command(BaseCommand):
    help = 'Erstellt Preview-Only und Face Swap Pipeline Templates'

    def handle(self, *args, **options):
        templates_created = []
        
        # Preview Only Template (für schnelle Iterationen)
        preview_only, created = PipelineTemplate.objects.get_or_create(
            name="Preview Only — Schnelle Iteration",
            defaults={
                'description': 'Nur Generierung + Preview Export. Kein Upscale, kein CMYK. Schnell & günstig für Iteration.',
                'category': 'custom',
                # Steps
                'step_generate': True,
                'step_face_swap': False,
                'step_upscale': False,       # ← DEAKTIVIERT für Speed
                'step_vectorize': False,
                'step_cmyk': False,
                'step_pod_export': False,
                'step_preview': True,
                'step_mockup': False,
                'step_auto_qa': False,
                # Defaults
                'default_width': 1024,
                'default_height': 1024,
                'default_dpi': 300,
                'default_steps': 4,
                'default_guidance': 7.0,
                'default_model': 'flux_schnell',
                'is_active': True,
            }
        )
        if created:
            templates_created.append('Preview Only')
            self.stdout.write(self.style.SUCCESS(f'✓ Created: {preview_only.name}'))
        else:
            self.stdout.write(self.style.WARNING(f'○ Already exists: {preview_only.name}'))
        
        # Face Swap Preview Template
        face_swap, created = PipelineTemplate.objects.get_or_create(
            name="Face Swap Preview",
            defaults={
                'description': 'Generierung → Face Swap → Preview. Für Portraits mit Gesichts-Ersetzung.',
                'category': 'custom',
                # Steps
                'step_generate': True,
                'step_face_swap': True,      # ← AKTIVIERT
                'step_upscale': False,       # ← DEAKTIVIERT für Speed
                'step_vectorize': False,
                'step_cmyk': False,
                'step_pod_export': False,
                'step_preview': True,
                'step_mockup': False,
                'step_auto_qa': False,
                # Defaults
                'default_width': 1024,
                'default_height': 1024,
                'default_dpi': 300,
                'default_steps': 4,
                'default_guidance': 7.0,
                'default_model': 'flux_schnell',
                'is_active': True,
            }
        )
        if created:
            templates_created.append('Face Swap Preview')
            self.stdout.write(self.style.SUCCESS(f'✓ Created: {face_swap.name}'))
        else:
            self.stdout.write(self.style.WARNING(f'○ Already exists: {face_swap.name}'))
        
        # Face Swap + Upscale (optional, für bessere Qualität)
        face_swap_hq, created = PipelineTemplate.objects.get_or_create(
            name="Face Swap High Quality",
            defaults={
                'description': 'Generierung → Face Swap → Upscale 4x → Preview. Beste Qualität.',
                'category': 'custom',
                # Steps
                'step_generate': True,
                'step_face_swap': True,      # ← AKTIVIERT
                'step_upscale': True,        # ← AKTIVIERT für Qualität
                'step_vectorize': False,
                'step_cmyk': False,
                'step_pod_export': True,     # POD Export nach Upscale
                'step_preview': True,
                'step_mockup': False,
                'step_auto_qa': False,
                # Defaults
                'default_width': 1024,
                'default_height': 1024,
                'default_dpi': 300,
                'default_steps': 4,
                'default_guidance': 7.0,
                'default_model': 'flux_schnell',
                'is_active': True,
            }
        )
        if created:
            templates_created.append('Face Swap High Quality')
            self.stdout.write(self.style.SUCCESS(f'✓ Created: {face_swap_hq.name}'))
        else:
            self.stdout.write(self.style.WARNING(f'○ Already exists: {face_swap_hq.name}'))
        
        # Summary
        if templates_created:
            self.stdout.write(self.style.SUCCESS(f'\n✓ {len(templates_created)} templates created: {", ".join(templates_created)}'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ All templates already exist'))
        
        # Zeige aktive Templates
        active_count = PipelineTemplate.objects.filter(is_active=True).count()
        self.stdout.write(self.style.SUCCESS(f'\nTotal active templates: {active_count}'))
