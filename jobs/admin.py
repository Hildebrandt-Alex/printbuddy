from django.contrib import admin
from django.utils import timezone
from .models import PipelineTemplate, Job, JobStep, PromptTemplate


class JobStepInline(admin.TabularInline):
    model  = JobStep
    extra  = 0
    readonly_fields = ('started_at', 'completed_at', 'output_asset_id')


def start_selected_jobs(modeladmin, request, queryset):
    """Custom Admin Action: Startet ausgewählte Draft-Jobs via Pipeline-Chain (ADR-11)."""
    from jobs.services import start_job

    started = 0
    skipped = 0
    for job in queryset.filter(status='draft'):
        try:
            start_job(str(job.id))
            started += 1
        except Exception as exc:
            modeladmin.message_user(request, f"Fehler bei Job '{job.title}': {exc}", level='error')
            skipped += 1

    if started:
        modeladmin.message_user(request, f"{started} Job(s) gestartet und in die Queue eingereiht.")
    if skipped:
        modeladmin.message_user(request, f"{skipped} Job(s) konnten nicht gestartet werden.", level='warning')

start_selected_jobs.short_description = "▶ Ausgewählte Jobs starten (Pipeline-Chain)"


@admin.register(PipelineTemplate)
class PipelineTemplateAdmin(admin.ModelAdmin):
    list_display  = ('name', 'category', 'default_model', 'default_steps', 'default_guidance', 'is_active')
    list_filter   = ('category', 'default_model', 'is_active')
    search_fields = ('name',)
    list_editable = ('is_active',)

    fieldsets = (
        ('1 — Modell wählen', {
            'description': (
                'Wähle zuerst das Modell. Die Parameter darunter werden automatisch vorausgefüllt.'
            ),
            'fields': ('default_model', 'name', 'description', 'category', 'is_active'),
        }),
        ('2 — Generierungsparameter', {
            'description': (
                '<strong>FLUX Schnell:</strong> Steps 4, Guidance 0 &nbsp;|&nbsp; '
                '<strong>SDXL:</strong> Steps 30, Guidance 7.5 &nbsp;|&nbsp; '
                '<strong>FLUX Dev:</strong> Steps 20, Guidance 3.5'
            ),
            'fields': (
                ('default_width', 'default_height'),
                ('default_steps', 'default_guidance'),
                'default_dpi',
            ),
        }),
        ('3 — Pipeline-Schritte', {
            'description': 'Für den ersten Test: nur Generate + Preview aktiv lassen.',
            'fields': (
                'step_generate',
                'step_upscale',
                'step_pod_export',
                'step_preview',
                'step_vectorize',
                'step_cmyk',
                'step_mockup',
                'step_auto_qa',
            ),
        }),
    )

    class Media:
        js = ('admin/js/pipeline_template_defaults.js',)


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display  = ('title', 'status', 'pipeline_template', 'created_by', 'created_at')
    list_filter   = ('status', 'pipeline_template')
    search_fields = ('title', 'prompt')
    readonly_fields = ('celery_chain_id', 'started_at', 'completed_at', 'created_at')
    inlines       = [JobStepInline]
    actions       = [start_selected_jobs]


@admin.register(PromptTemplate)
class PromptTemplateAdmin(admin.ModelAdmin):
    list_display  = ('title', 'category', 'is_public', 'created_at')
    list_filter   = ('category', 'is_public')
    search_fields = ('title', 'base_text')

