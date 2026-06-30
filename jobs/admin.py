from django.contrib import admin
from django.utils import timezone
from .models import PipelineTemplate, Job, JobStep, PromptTemplate


class JobStepInline(admin.TabularInline):
    model  = JobStep
    extra  = 0
    readonly_fields = ('step_type', 'order', 'status', 'started_at', 'completed_at', 'output_asset_id', 'error_msg')
    fields          = ('order', 'step_type', 'status', 'started_at', 'completed_at', 'output_asset_id', 'error_msg')

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


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
    list_display   = ('title', 'status', 'pipeline_template', 'output_type_badge', 'created_by', 'created_at')
    list_filter    = ('status', 'pipeline_template__default_model')
    search_fields  = ('title', 'prompt')
    actions        = [start_selected_jobs]
    inlines        = [JobStepInline]

    # ── Alles readonly — kein Bearbeiten, nur Anzeigen + Starten ────────────
    readonly_fields = (
        'title', 'status', 'pipeline_template', 'created_by', 'created_at',
        'started_at', 'completed_at', 'celery_chain_id', 'notes',
        'template_defaults_info', 'user_overrides_info', 'prompt_display',
    )

    fieldsets = (
        ('Job', {
            'fields': ('title', 'status', 'pipeline_template', 'created_by', 'created_at',
                       'started_at', 'completed_at', 'celery_chain_id'),
        }),
        ('Prompt', {
            'fields': ('prompt_display',),
        }),
        ('Template-Defaults (aus Pipeline-Template)', {
            'fields': ('template_defaults_info',),
        }),
        ('User-Overrides (aus Studio-Formular)', {
            'description': 'Leer = Template-Default wird verwendet.',
            'fields': ('user_overrides_info',),
        }),
        ('Notizen', {
            'fields': ('notes',),
            'classes': ('collapse',),
        }),
    )

    def has_add_permission(self, request):
        return False  # Jobs nur über Studio anlegen

    def has_change_permission(self, request, obj=None):
        return False  # Kein Bearbeiten — nur Admin-Aktionen

    @admin.display(description='Prompt')
    def prompt_display(self, obj):
        from django.utils.html import format_html
        neg = f'<br><small style="color:#888">Negativ: {obj.negative_prompt}</small>' if obj.negative_prompt else ''
        return format_html('<span style="white-space:pre-wrap">{}</span>{}', obj.prompt, neg)

    @admin.display(description='Template-Defaults')
    def template_defaults_info(self, obj):
        from django.utils.html import format_html
        t = obj.pipeline_template
        steps = []
        if t.step_generate:   steps.append('generate')
        if t.step_upscale:    steps.append('upscale')
        if t.step_pod_export: steps.append('pod_export')
        if t.step_preview:    steps.append('preview')
        if t.step_vectorize:  steps.append('vectorize')
        if t.step_cmyk:       steps.append('cmyk')
        if t.step_mockup:     steps.append('mockup')
        if t.step_auto_qa:    steps.append('auto_qa')
        return format_html(
            '<code>Modell: {} &nbsp;|&nbsp; {}×{} px &nbsp;|&nbsp; '
            'Steps: {} &nbsp;|&nbsp; Guidance: {}</code><br>'
            '<small style="color:#888">Pipeline: {}</small>',
            t.default_model, t.default_width, t.default_height,
            t.default_steps, t.default_guidance,
            ' → '.join(steps),
        )

    @admin.display(description='User-Overrides')
    def user_overrides_info(self, obj):
        from django.utils.html import format_html
        parts = []
        if obj.model:      parts.append(f'Modell: {obj.model}')
        if obj.width:      parts.append(f'Breite: {obj.width}')
        if obj.height:     parts.append(f'Höhe: {obj.height}')
        if obj.num_steps:  parts.append(f'Steps: {obj.num_steps}')
        if obj.guidance:   parts.append(f'Guidance: {obj.guidance}')
        if obj.seed:       parts.append(f'Seed: {obj.seed}')
        if obj.num_images and obj.num_images > 1:
            parts.append(f'Bilder: {obj.num_images}')
        if not parts:
            return format_html('<span style="color:#888">— Keine Overrides, Template-Defaults werden verwendet —</span>')
        return format_html('<code>{}</code>', ' &nbsp;|&nbsp; '.join(parts))

    @admin.display(description='Output-Typ')
    def output_type_badge(self, obj):
        from django.utils.html import format_html
        cat = obj.pipeline_template.category if obj.pipeline_template else ''
        colors = {
            'card_pod': ('#1e3a5f', '#93c5fd'),
            'poster_offset': ('#3b1e6d', '#c4b5fd'),
            'shirt_batch': ('#14532d', '#86efac'),
            'vector_art': ('#78350f', '#fde68a'),
            'custom': ('#334155', '#94a3b8'),
        }
        bg, fg = colors.get(cat, ('#334155', '#94a3b8'))
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;border-radius:12px;font-size:.75rem;font-weight:600">{}</span>',
            bg, fg, obj.pipeline_template.get_category_display() if obj.pipeline_template else '—'
        )


@admin.register(PromptTemplate)
class PromptTemplateAdmin(admin.ModelAdmin):
    list_display  = ('title', 'category', 'is_public', 'created_at')
    list_filter   = ('category', 'is_public')
    search_fields = ('title', 'base_text')

