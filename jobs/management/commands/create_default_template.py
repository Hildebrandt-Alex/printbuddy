"""
Management Command: Erstellt das Standard FLUX Schnell Pipeline Template.

Usage:
    python manage.py create_default_template
"""

from django.core.management.base import BaseCommand
from jobs.models import PipelineTemplate


class Command(BaseCommand):
    help = "Erstellt das Standard FLUX Schnell Pipeline Template für Production"

    def handle(self, *args, **options):
        # Prüfe ob bereits ein Template existiert
        existing = PipelineTemplate.objects.filter(name="FLUX Schnell — Standard").first()
        
        if existing:
            self.stdout.write(
                self.style.WARNING(
                    f'Template "{existing.name}" existiert bereits (ID: {existing.id})'
                )
            )
            self.stdout.write("Keine Änderungen vorgenommen.")
            return

        # Erstelle FLUX Schnell Standard Template
        template = PipelineTemplate.objects.create(
            name="FLUX Schnell — Standard",
            description="Standard-Pipeline für kommerzielle Bildgenerierung mit FLUX Schnell (Apache 2.0 Lizenz)",
            category="custom",
            # Pipeline Steps — nur das Nötigste für MVP
            step_generate=True,
            step_upscale=False,      # Später aktivieren wenn GPU-Budget erlaubt
            step_vectorize=False,    # Nur für Vector Art
            step_cmyk=False,         # Nur für Offset-Druck
            step_pod_export=True,    # PNG 300dpi für Print-on-Demand
            step_preview=True,       # Immer für Galerie
            step_mockup=False,       # Später aktivieren wenn Printful-Integration fertig
            step_auto_qa=False,      # Später aktivieren wenn QA-Pipeline steht
            # Default Generation Parameters
            default_width=1024,
            default_height=1024,
            default_dpi=300,
            default_steps=30,
            default_guidance=7.5,
            default_model="flux_schnell",  # Apache 2.0 — kommerziell erlaubt
            is_active=True,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Template "{template.name}" erfolgreich erstellt!'
            )
        )
        self.stdout.write(f"   ID: {template.id}")
        self.stdout.write(f"   Model: {template.default_model}")
        self.stdout.write(f"   Steps: generate → pod_export → preview → notify")
        self.stdout.write(
            "\nDieses Template kann jetzt im Studio für Job-Erstellung verwendet werden."
        )
