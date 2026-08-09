"""
Management Command: Enhancement-Only Pipeline Templates erstellen

Erstellt Template für Post-Processing ohne GPU-Generierung:
- Enhancement Only — Post-Processing (kein generate, nur Verbesserungen)

Usage:
    python manage.py create_enhancement_templates
"""

from django.core.management.base import BaseCommand
from jobs.models import PipelineTemplate


class Command(BaseCommand):
    help = "Erstellt Enhancement-Only Pipeline Template"

    def handle(self, *args, **options):
        self.stdout.write("=" * 70)
        self.stdout.write("Enhancement-Only Template erstellen")
        self.stdout.write("=" * 70)

        # Template 1: Enhancement Only (kein generate)
        template, created = PipelineTemplate.objects.get_or_create(
            name="Enhancement Only — Post-Processing",
            defaults={
                "description": (
                    "Post-Processing ohne Neugenerierung. "
                    "Nutzt bestehendes Preview-Asset als Input. "
                    "Aktivierte Steps werden per Job-Notes gesteuert."
                ),
                "category": "custom",
                # WICHTIG: Kein generate!
                "step_generate": False,
                # Steps werden per Job dynamisch aktiviert
                "step_upscale": False,
                "step_vectorize": False,
                "step_cmyk": False,
                "step_pod_export": False,
                "step_preview": True,  # Immer preview am Ende
                "step_mockup": False,
                "step_auto_qa": False,
                "step_face_swap": False,
                # Default-Parameter (unwichtig, da kein generate)
                "default_width": 1024,
                "default_height": 1024,
                "default_dpi": 300,
                "default_steps": 4,
                "default_guidance": 7.5,
                "default_model": "flux_schnell",
                "is_active": True,
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS("✓ Created: Enhancement Only"))
        else:
            self.stdout.write(self.style.WARNING("⚠ Already exists: Enhancement Only"))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(self.style.SUCCESS("✓ Enhancement Template bereit"))
        self.stdout.write(self.style.SUCCESS("=" * 70))

        # Status
        total = PipelineTemplate.objects.filter(is_active=True).count()
        self.stdout.write(f"\nTotal active templates: {total}")
