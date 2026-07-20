import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify

User = get_user_model()


class Project(models.Model):
    """
    Organisiert Jobs und Assets in Projekten für bessere Übersicht.
    Ermöglicht Team-Kollaboration und Asset-Management.
    """
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title         = models.CharField(max_length=120)
    slug          = models.SlugField(unique=True, max_length=140)
    description   = models.TextField(blank=True, help_text="Projekt-Beschreibung, Ziel, Notizen")
    created_by    = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_projects')
    team_members  = models.ManyToManyField(User, related_name='projects', blank=True, 
                                           help_text="Teammitglieder die Projekt sehen können")
    is_active     = models.BooleanField(default=True, help_text="Inaktive Projekte archiviert")
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Projekt'
        verbose_name_plural = 'Projekte'

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Project.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_job_count(self):
        """Anzahl Jobs in diesem Projekt."""
        return self.jobs.count()

    def get_asset_count(self):
        """Anzahl Gallery-Images in diesem Projekt."""
        return self.gallery_images.count()


class PipelineTemplate(models.Model):
    class Category(models.TextChoices):
        SHIRT_BATCH   = 'shirt_batch',   'Shirt Batch'
        POSTER_OFFSET = 'poster_offset', 'Poster Offset'
        CARD_POD      = 'card_pod',      'Karte POD'
        VECTOR_ART    = 'vector_art',    'Vektor Art'
        CUSTOM        = 'custom',        'Custom'

    class Model(models.TextChoices):
        FLUX_SCHNELL = 'flux_schnell', 'FLUX Schnell (Apache 2.0 — kommerziell OK)'
        FLUX_DEV     = 'flux_dev',     'FLUX Dev (NICHT für Verkauf!)'
        SDXL         = 'sdxl',         'SDXL (kommerziell OK)'
        CUSTOM_LORA  = 'custom_lora',  'Custom LoRA (Lizenz prüfen!)'

    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name             = models.CharField(max_length=100)
    description      = models.TextField(blank=True)
    category         = models.CharField(max_length=30, choices=Category.choices)
    # Pipeline Steps
    step_generate    = models.BooleanField(default=True)
    step_face_swap   = models.BooleanField(default=False, help_text="Gesicht aus reference_image auf generiertes Bild übertragen")
    step_upscale     = models.BooleanField(default=True)
    step_vectorize   = models.BooleanField(default=False)
    step_cmyk        = models.BooleanField(default=False)
    step_pod_export  = models.BooleanField(default=True)
    step_preview     = models.BooleanField(default=True)
    step_mockup      = models.BooleanField(default=False)
    step_auto_qa     = models.BooleanField(default=False)
    # Default Generation Parameters
    default_width    = models.PositiveIntegerField(default=1024)
    default_height   = models.PositiveIntegerField(default=1024)
    default_dpi      = models.PositiveIntegerField(default=300)
    default_steps    = models.PositiveIntegerField(default=30)
    default_guidance = models.FloatField(default=7.5)
    default_model    = models.CharField(max_length=30, choices=Model.choices, default=Model.FLUX_SCHNELL)
    is_active        = models.BooleanField(default=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Pipeline-Template'
        verbose_name_plural = 'Pipeline-Templates'

    def __str__(self):
        return self.name


class Job(models.Model):
    class Status(models.TextChoices):
        DRAFT     = 'draft',     'Entwurf'
        QUEUED    = 'queued',    'In Warteschlange'
        RUNNING   = 'running',   'Läuft'
        DONE      = 'done',      'Fertig'
        FAILED    = 'failed',    'Fehlgeschlagen'
        CANCELLED = 'cancelled', 'Abgebrochen'

    id                = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title             = models.CharField(max_length=150)
    status            = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    pipeline_template = models.ForeignKey(PipelineTemplate, on_delete=models.PROTECT, null=True, blank=True,
                                          help_text="Pipeline wird nach Bildgenerierung im Produkt-Wizard zugewiesen")
    project           = models.ForeignKey('Project', on_delete=models.SET_NULL, null=True, blank=True,
                                          related_name='jobs', help_text="Projekt-Zuordnung (optional)")
    prompt            = models.TextField()
    negative_prompt   = models.TextField(blank=True)
    reference_image   = models.ImageField(upload_to='jobs/refs/', blank=True)
    # Parameter Overrides
    width      = models.PositiveIntegerField(null=True, blank=True)
    height     = models.PositiveIntegerField(null=True, blank=True)
    num_images = models.PositiveIntegerField(default=1)
    model      = models.CharField(max_length=30, blank=True)
    num_steps  = models.PositiveIntegerField(null=True, blank=True)
    guidance   = models.FloatField(null=True, blank=True)
    seed       = models.BigIntegerField(null=True, blank=True)
    # Tracking
    created_by      = models.ForeignKey(User, on_delete=models.PROTECT)
    celery_chain_id = models.CharField(max_length=100, blank=True)
    notes           = models.TextField(blank=True)
    started_at      = models.DateTimeField(null=True, blank=True)
    completed_at    = models.DateTimeField(null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Job'
        verbose_name_plural = 'Jobs'

    def __str__(self):
        return f"{self.title} [{self.status}]"


class JobStep(models.Model):
    class StepType(models.TextChoices):
        GENERATE       = 'generate',       'Generierung'
        UPSCALE        = 'upscale',        'Upscaling'
        VECTORIZE      = 'vectorize',      'Vektorisierung'
        CMYK_EXPORT    = 'cmyk_export',    'CMYK Export'
        POD_EXPORT     = 'pod_export',     'POD Export'
        PREVIEW_EXPORT = 'preview_export', 'Preview Export'
        MOCKUP_GEN     = 'mockup_gen',     'Mockup Generierung'
        AUTO_QA        = 'auto_qa',        'Auto QA'
        NOTIFY_STUDIO  = 'notify_studio',  'Studio-Benachrichtigung'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Ausstehend'
        RUNNING = 'running', 'Läuft'
        DONE    = 'done',    'Fertig'
        SKIPPED = 'skipped', 'Übersprungen'
        FAILED  = 'failed',  'Fehlgeschlagen'

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job             = models.ForeignKey(Job, related_name='steps', on_delete=models.CASCADE)
    step_type       = models.CharField(max_length=30, choices=StepType.choices)
    order           = models.PositiveIntegerField()
    status          = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    params          = models.JSONField(default=dict)
    output_asset_id = models.UUIDField(null=True, blank=True)
    started_at      = models.DateTimeField(null=True, blank=True)
    completed_at    = models.DateTimeField(null=True, blank=True)
    error_msg       = models.TextField(blank=True)

    class Meta:
        ordering = ['order']
        verbose_name = 'Job-Step'
        verbose_name_plural = 'Job-Steps'

    def __str__(self):
        return f"{self.job.title} — {self.step_type} [{self.status}]"


class PromptTemplate(models.Model):
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title          = models.CharField(max_length=150)
    category       = models.CharField(max_length=60)
    base_text      = models.TextField()
    variables      = models.JSONField(default=dict)
    example_output = models.ImageField(upload_to='jobs/prompt_examples/', blank=True)
    is_public      = models.BooleanField(default=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Prompt-Template'
        verbose_name_plural = 'Prompt-Templates'

    def __str__(self):
        return self.title

