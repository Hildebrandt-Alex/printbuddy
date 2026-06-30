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
    list_display  = ('name', 'category', 'default_model', 'is_active', 'created_at')
    list_filter   = ('category', 'default_model', 'is_active')
    search_fields = ('name',)
    list_editable = ('is_active',)


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

