"""
Management Command: Zeigt aktive Pipeline-Template-Konfiguration.

Usage:
    python manage.py show_pipeline_config
"""

from django.core.management.base import BaseCommand
from jobs.models import PipelineTemplate, Job


class Command(BaseCommand):
    help = "Zeigt aktive Pipeline-Template-Konfiguration und Job-Status"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(self.style.SUCCESS("PrintBuddy Pipeline-Konfiguration"))
        self.stdout.write(self.style.SUCCESS("=" * 70))
        
        # Alle Templates
        templates = PipelineTemplate.objects.all()
        active_templates = templates.filter(is_active=True)
        
        self.stdout.write(f"\n📋 Pipeline Templates:")
        self.stdout.write(f"   Insgesamt: {templates.count()}")
        self.stdout.write(f"   Aktiv: {active_templates.count()}")
        
        if not templates.exists():
            self.stdout.write(self.style.ERROR("\n❌ KEINE Templates vorhanden!"))
            self.stdout.write("   Führe aus: python manage.py create_default_template")
            return
        
        self.stdout.write("\n" + "-" * 70)
        
        for t in templates:
            status_icon = "✅" if t.is_active else "⏸️"
            self.stdout.write(f"\n{status_icon} Template: {t.name}")
            self.stdout.write(f"   ID: {t.id}")
            self.stdout.write(f"   Model: {t.default_model}")
            self.stdout.write(f"   Category: {t.category}")
            self.stdout.write(f"   Active: {t.is_active}")
            
            self.stdout.write("\n   Pipeline Steps:")
            steps = []
            if t.step_generate:    steps.append("generate")
            if t.step_upscale:     steps.append("upscale")
            if t.step_vectorize:   steps.append("vectorize")
            if t.step_cmyk:        steps.append("cmyk_export")
            if t.step_pod_export:  steps.append("pod_export")
            if t.step_preview:     steps.append("preview")
            if t.step_mockup:      steps.append("mockup_gen")
            if t.step_auto_qa:     steps.append("auto_qa")
            
            for step in steps:
                self.stdout.write(f"     → {step}")
        
        # Job-Statistiken
        self.stdout.write("\n" + "-" * 70)
        self.stdout.write("\n💼 Job-Statistik:")
        
        total_jobs = Job.objects.count()
        jobs_without_template = Job.objects.filter(pipeline_template__isnull=True).count()
        jobs_by_status = Job.objects.values('status').annotate(count=models.Count('id'))
        
        self.stdout.write(f"   Total Jobs: {total_jobs}")
        
        if jobs_without_template > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"   ⚠️ Jobs ohne Template: {jobs_without_template}"
                )
            )
            self.stdout.write("      Diese müssen manuell repariert werden!")
        
        self.stdout.write("\n   Jobs nach Status:")
        for item in jobs_by_status:
            status = item['status']
            count = item['count']
            icon_map = {
                'draft': '📝',
                'queued': '⏸️',
                'running': '▶️',
                'done': '✅',
                'failed': '❌',
                'cancelled': '🚫'
            }
            icon = icon_map.get(status, '❓')
            self.stdout.write(f"     {icon} {status}: {count}")
        
        self.stdout.write("\n" + "=" * 70)
        
        if active_templates.count() == 0:
            self.stdout.write(
                self.style.WARNING(
                    "\n⚠️ WARNUNG: Kein aktives Template! Jobs können nicht erstellt werden."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✅ System ist bereit. Aktives Template: {active_templates.first().name}"
                )
            )


# Django models import for aggregation
from django.db import models
