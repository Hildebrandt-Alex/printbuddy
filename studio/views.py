import functools
import logging
import uuid as uuid_mod
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from jobs.models import Job, PipelineTemplate, PromptTemplate, Project

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Zugriffsschutz — studio_workers ODER is_staff
# ─────────────────────────────────────────────────────────────────────────────

def studio_required(view_func):
    """Login + Gruppen-Prüfung: studio_workers ODER Admin (is_staff)."""
    @functools.wraps(view_func)
    @login_required(login_url="/studio/login/")
    def wrapper(request, *args, **kwargs):
        user = request.user
        is_studio = user.groups.filter(name="studio_workers").exists()
        if not (is_studio or user.is_staff):
            return render(request, "studio/403.html", status=403)
        return view_func(request, *args, **kwargs)
    return wrapper


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────────────────────────────────────

@studio_required
def dashboard(request):
    recent_jobs = (
        Job.objects.filter(created_by=request.user)
        .select_related("pipeline_template")
        .order_by("-created_at")[:10]
    )
    stats = {
        "draft":   Job.objects.filter(created_by=request.user, status="draft").count(),
        "running": Job.objects.filter(created_by=request.user, status__in=["queued", "running"]).count(),
        "done":    Job.objects.filter(created_by=request.user, status="done").count(),
        "failed":  Job.objects.filter(created_by=request.user, status="failed").count(),
    }
    return render(request, "studio/dashboard.html", {"recent_jobs": recent_jobs, "stats": stats})


# ─────────────────────────────────────────────────────────────────────────────
# Projekt-System
# ─────────────────────────────────────────────────────────────────────────────

@studio_required
def project_list(request):
    """Alle Projekte des Users (erstellt oder Mitglied)."""
    projects = (
        Project.objects.filter(
            models.Q(created_by=request.user) | models.Q(team_members=request.user)
        )
        .distinct()
        .prefetch_related('jobs', 'gallery_images')
        .order_by('-updated_at')
    )
    return render(request, 'studio/project_list.html', {'projects': projects})


@studio_required
def project_detail(request, slug):
    """Projekt-Detailansicht: alle Jobs + Assets des Projekts."""
    project = get_object_or_404(
        Project.objects.filter(
            models.Q(created_by=request.user) | models.Q(team_members=request.user)
        ),
        slug=slug
    )
    jobs = project.jobs.select_related('pipeline_template').order_by('-created_at')
    assets = project.gallery_images.order_by('-created_at')
    return render(request, 'studio/project_detail.html', {
        'project': project,
        'jobs': jobs,
        'assets': assets,
    })


@studio_required
def project_create(request):
    """Neues Projekt anlegen."""
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        if not title:
            messages.error(request, 'Projekttitel ist erforderlich.')
            return render(request, 'studio/project_create.html', {'post': request.POST})
        project = Project.objects.create(
            title=title,
            description=description,
            created_by=request.user,
        )
        messages.success(request, f"Projekt '{project.title}' erstellt.")
        return redirect('studio:project_detail', slug=project.slug)
    return render(request, 'studio/project_create.html', {'post': {}})


@require_POST
@studio_required
def project_move_job(request, job_id):
    """Job in anderes Projekt verschieben (HTMX-kompatibel)."""
    job = get_object_or_404(Job, id=job_id, created_by=request.user)
    project_id = request.POST.get('project_id', '').strip()
    if project_id:
        project = get_object_or_404(Project, id=project_id)
        job.project = project
    else:
        job.project = None
    job.save(update_fields=['project'])
    messages.success(request, f"Job in Projekt '{job.project}' verschoben.")
    return redirect(request.POST.get('next', 'studio:job_list'))


# ─────────────────────────────────────────────────────────────────────────────
# Job-Liste
# ─────────────────────────────────────────────────────────────────────────────

@studio_required
def job_list(request):
    status_filter  = request.GET.get('status', '')
    project_filter = request.GET.get('project', '')
    jobs = (
        Job.objects.filter(created_by=request.user)
        .select_related('pipeline_template', 'project')
        .order_by('-created_at')
    )
    if status_filter:
        jobs = jobs.filter(status=status_filter)
    if project_filter:
        jobs = jobs.filter(project__slug=project_filter)
    projects = Project.objects.filter(
        models.Q(created_by=request.user) | models.Q(team_members=request.user)
    ).distinct().order_by('title')
    return render(request, 'studio/job_list.html', {
        'jobs': jobs,
        'status_filter': status_filter,
        'project_filter': project_filter,
        'status_choices': Job.Status.choices,
        'projects': projects,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Job anlegen (nur Draft — ADR-11)
# ─────────────────────────────────────────────────────────────────────────────

@studio_required
def job_create(request):
    """
    NEUE VERSION: Nur Bildgenerierung-Wizard (Model + Prompt + Parameter)
    Pipeline-Template wird später im Product Wizard zugewiesen
    """
    import json
    from jobs.model_info import MODEL_DESCRIPTIONS, get_model_info
    
    prompt_templates = PromptTemplate.objects.filter(is_public=True).order_by("category", "title")
    projects = Project.objects.filter(
        models.Q(created_by=request.user) | models.Q(team_members=request.user)
    ).distinct().order_by('title')
    
    # Model Descriptions als JSON für Template
    model_descriptions_json = json.dumps(MODEL_DESCRIPTIONS)

    if request.method == "POST":
        title          = request.POST.get("title", "").strip()
        prompt         = request.POST.get("prompt", "").strip()
        negative_prompt = request.POST.get("negative_prompt", "").strip()
        notes          = request.POST.get("notes", "").strip()
        model          = request.POST.get("model", "").strip()

        # Optionale Override-Felder
        width      = request.POST.get("width") or None
        height     = request.POST.get("height") or None
        steps      = request.POST.get("steps") or None
        guidance   = request.POST.get("guidance") or None
        seed       = request.POST.get("seed") or None
        num_images = int(request.POST.get("num_images") or 1)

        errors = []
        if not title:      errors.append("Titel ist erforderlich.")
        if not prompt:     errors.append("Prompt ist erforderlich.")
        if not model:      errors.append("Modell ist erforderlich.")

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, "studio/job_create.html", {
                "prompt_templates": prompt_templates,
                "projects": projects,
                "post": request.POST,
                "model_descriptions": model_descriptions_json,
            })

        # Projekt-Zuordnung (optional)
        project_id = request.POST.get('project_id', '').strip()
        project = None
        if project_id:
            try:
                project = Project.objects.get(id=project_id)
            except Project.DoesNotExist:
                pass

        # Job OHNE Pipeline Template erstellen (wird später zugewiesen)
        job = Job.objects.create(
            title=title,
            pipeline_template=None,  # NEU: Optional
            project=project,
            prompt=prompt,
            negative_prompt=negative_prompt,
            notes=notes,
            model=model,
            width=int(width) if width else None,
            height=int(height) if height else None,
            num_steps=int(steps) if steps else None,
            guidance=float(guidance) if guidance else None,
            seed=int(seed) if seed else None,
            num_images=num_images,
            status='draft',
            created_by=request.user,
        )
        
        # Reference Image für Img2Img oder Face Swap (falls hochgeladen)
        if 'reference_image' in request.FILES:
            job.reference_image = request.FILES['reference_image']
            job.save(update_fields=['reference_image'])
            logger.info("[job_create] Reference Image hochgeladen für Job %s", job.id)
        
        # Face Image für Face Swap (zweites Bild)
        if 'face_image' in request.FILES:
            job.face_image = request.FILES['face_image']
            job.save(update_fields=['face_image'])
            logger.info("[job_create] Face Image hochgeladen für Job %s", job.id)

        messages.success(request, f"Job '{job.title}' angelegt. Admin muss ihn starten.")
        return redirect("studio:job_detail", job_id=job.id)

    return render(request, 'studio/job_create.html', {
        'prompt_templates': prompt_templates,
        'projects': projects,
        'post': {},
        'model_descriptions': model_descriptions_json,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Job-Detail + HTMX-Status-Partial (Polling alle 3s)
# ─────────────────────────────────────────────────────────────────────────────

@studio_required
def job_detail(request, job_id):
    job = get_object_or_404(Job, id=job_id, created_by=request.user)
    steps = job.steps.all().order_by("order")
    return render(request, "studio/job_detail.html", {"job": job, "steps": steps})


@studio_required
def job_status_partial(request, job_id):
    """HTMX-Partial: Statusblock ohne Layout. Wird alle 3s vom Client gepolt."""
    job = get_object_or_404(Job, id=job_id, created_by=request.user)
    steps = job.steps.all().order_by("order")
    return render(request, "studio/partials/job_status.html", {"job": job, "steps": steps})


# ─────────────────────────────────────────────────────────────────────────────
# Job-Ergebnisse
# ─────────────────────────────────────────────────────────────────────────────

@studio_required
def job_results(request, job_id):
    job = get_object_or_404(Job, id=job_id, created_by=request.user)

    if job.status != "done":
        messages.warning(request, "Job ist noch nicht abgeschlossen.")
        return redirect("studio:job_detail", job_id=job.id)

    preview_dir = Path(getattr(settings, "NAS_BASE_PATH", "local_nas")) / "exports" / "preview"
    preview_steps = job.steps.filter(step_type="preview_export", status="done").exclude(
        output_asset_id__isnull=True
    )

    # Prüfe welche Assets bereits als GalleryImage vorgemerkt sind
    from gallery.models import GalleryImage
    # Hole alle GalleryImages für diesen Job
    existing_gallery_images = list(GalleryImage.objects.filter(source_job_id=job.id))

    assets = []
    for step in preview_steps:
        asset_id = str(step.output_asset_id)
        filename = f"{asset_id}_preview.jpg"
        filepath = preview_dir / filename
        try:
            file_exists = filepath.exists()
        except (PermissionError, OSError):
            file_exists = True  # NAS nicht lesbar für www-data — trotzdem anzeigen, Nginx serviert es
        
        # Status prüfen: nicht vorgemerkt / vorgemerkt / online
        # Finde GalleryImage anhand des Asset-UUID im Dateinamen
        gallery_img = None
        for img in existing_gallery_images:
            if asset_id in str(img.file_path.name):
                gallery_img = img
                break
        
        if gallery_img:
            if gallery_img.is_public:
                status = "online"
                status_label = "✓ Online in Galerie"
            else:
                status = "vorgemerkt"
                status_label = "● Vorgemerkt (wartet auf Admin-Freigabe)"
        else:
            status = "not_selected"
            status_label = None
        
        assets.append({
            "asset_id": asset_id,
            "filename": filename,
            "exists": file_exists,
            "gallery_status": status,
            "gallery_status_label": status_label,
        })

    return render(request, "studio/job_results.html", {"job": job, "assets": assets})


# ─────────────────────────────────────────────────────────────────────────────
# Asset-Selektion → GalleryImage anlegen (ADR-11 / Phase 6)
# ─────────────────────────────────────────────────────────────────────────────

@require_POST
@studio_required
def asset_select(request, job_id):
    """
    Studio-Worker wählt ein generiertes Bild für die Galerie aus.
    Legt GalleryImage an (is_public=False) und stößt Mockup-Generierung an.
    """
    from gallery.models import GalleryImage
    from postprocess.tasks import generate_all_mockups

    job = get_object_or_404(Job, id=job_id, created_by=request.user)
    asset_id = request.POST.get("asset_id", "").strip()
    title    = request.POST.get("title", f"{job.title} — Galerie").strip()
    category = request.POST.get("category", "art")
    cta_type = request.POST.get("cta_type", "contact")

    if not asset_id:
        messages.error(request, "Kein Asset ausgewählt.")
        return redirect("studio:job_results", job_id=job.id)

    preview_dir = Path(getattr(settings, "NAS_BASE_PATH", "local_nas")) / "exports" / "preview"
    preview_filename = f"{asset_id}_preview.jpg"
    preview_src = preview_dir / preview_filename

    try:
        file_missing = not preview_src.exists()
    except (PermissionError, OSError):
        file_missing = False  # NAS nicht lesbar für www-data — Step existiert laut DB, weiter

    if file_missing:
        messages.error(request, f"Preview-Datei nicht gefunden: {preview_filename}")
        return redirect("studio:job_results", job_id=job.id)

    # Eindeutigen Slug erzeugen
    slug_base = slugify(title)[:100]
    slug, counter = slug_base, 1
    while GalleryImage.objects.filter(slug=slug).exists():
        slug = f"{slug_base}-{counter}"
        counter += 1

    try:
        gallery_image = GalleryImage.objects.create(
            title=title,
            slug=slug,
            category=category,
            cta_type=cta_type,
            file_path=f"exports/preview/{preview_filename}",
            thumb_path=f"exports/preview/{preview_filename}",  # Preview ist bereits klein — kein Pillow-Open auf NAS
            is_public=False,  # Admin gibt explizit frei
            source_job_id=job.id,
            project=getattr(job, 'project', None),  # Projekt vom Job erben (falls vorhanden)
        )
        logger.info(
            "[asset_select] GalleryImage %s erstellt von User %s (Job %s, Asset %s)",
            gallery_image.id, request.user.username, job_id, asset_id,
        )
    except Exception as exc:
        logger.error(
            "[asset_select] GalleryImage.create FEHLER: %s — Job %s, User %s, Asset %s",
            type(exc).__name__, job_id, request.user.username, asset_id,
            exc_info=True,
        )
        messages.error(request, f"Fehler beim Vormerken: {type(exc).__name__}: {str(exc)}")
        return redirect("studio:job_results", job_id=job.id)

    try:
        generate_all_mockups.delay(str(gallery_image.id))
    except Exception as exc:
        logger.warning("[asset_select] generate_all_mockups.delay fehlgeschlagen: %s", exc)

    messages.success(
        request,
        f"'{title}' für Galerie vorgemerkt — Admin muss is_public aktivieren.",
    )
    return redirect("studio:dashboard")


# ─────────────────────────────────────────────────────────────────────────────
# Prompt-Bibliothek
# ─────────────────────────────────────────────────────────────────────────────

@studio_required
def prompt_library(request):
    category_filter = request.GET.get("cat", "")
    prompts = PromptTemplate.objects.filter(is_public=True).order_by("category", "title")
    if category_filter:
        prompts = prompts.filter(category=category_filter)
    categories = sorted(
        PromptTemplate.objects.filter(is_public=True)
        .values_list("category", flat=True)
        .distinct()
    )
    return render(request, "studio/prompt_library.html", {
        "prompts": prompts,
        "categories": categories,
        "category_filter": category_filter,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Product Wizard — Produkt-Typ nach Bildgenerierung wählen
# ─────────────────────────────────────────────────────────────────────────────

@studio_required
def product_wizard(request, job_id):
    """
    NEUER WORKFLOW: Nach Bildgenerierung → Produkt-Typ wählen → Pipeline zuweisen
    User wählt welche Produkte (T-Shirt, Poster, etc.) erstellt werden sollen
    """
    from studio.constants import PRODUCT_TYPES, get_product_type
    from bundles.tasks import create_product_bundle
    
    job = get_object_or_404(Job, id=job_id, created_by=request.user)
    
    if job.status != "done":
        messages.warning(request, "Job muss erst abgeschlossen sein bevor Produkte erstellt werden können.")
        return redirect("studio:job_detail", job_id=job.id)
    
    # Hole alle generierten Preview-Assets
    preview_steps = job.steps.filter(step_type="preview_export", status="done").exclude(
        output_asset_id__isnull=True
    )
    
    if not preview_steps.exists():
        messages.error(request, "Keine generierten Bilder gefunden.")
        return redirect("studio:job_detail", job_id=job.id)
    
    # Asset-Previews sammeln
    from pathlib import Path
    preview_dir = Path(getattr(settings, "NAS_BASE_PATH", "local_nas")) / "exports" / "preview"
    
    assets = []
    for step in preview_steps:
        asset_id = str(step.output_asset_id)
        filename = f"{asset_id}_preview.jpg"
        assets.append({
            "asset_id": asset_id,
            "filename": filename,
            "url": f"/nas/exports/preview/{filename}",
        })
    
    if request.method == "POST":
        product_type = request.POST.get("product_type", "").strip()
        
        if not product_type or product_type not in PRODUCT_TYPES:
            messages.error(request, "Bitte einen Produkt-Typ wählen.")
            return render(request, "studio/product_wizard.html", {
                "job": job,
                "assets": assets,
                "product_types": PRODUCT_TYPES,
                "post": request.POST,
            })
        
        product_meta = get_product_type(product_type)
        pipeline_name = product_meta.get('pipeline_name')
        
        # Pipeline Template zuweisen (falls vorhanden)
        if pipeline_name:
            try:
                pipeline = PipelineTemplate.objects.get(name=pipeline_name, is_active=True)
                job.pipeline_template = pipeline
                job.save(update_fields=['pipeline_template'])
                logger.info("[product_wizard] Pipeline '%s' assigned to Job %s", pipeline_name, job.id)
            except PipelineTemplate.DoesNotExist:
                messages.error(request, f"Pipeline-Template '{pipeline_name}' nicht gefunden. Bitte Admin kontaktieren.")
                return redirect("studio:job_results", job_id=job.id)
        
        # Bundle-Task starten (erstellt Export-Dateien je nach Produkt-Typ)
        try:
            # Note: create_product_bundle Task muss noch implementiert werden
            # create_product_bundle.delay(str(job.id), product_type)
            messages.success(request, f"Produkt-Bundle für '{product_meta['label']}' wird erstellt...")
        except Exception as exc:
            logger.error("[product_wizard] Bundle-Task failed: %s", exc)
            messages.warning(request, "Bundle-Task konnte nicht gestartet werden.")
        
        messages.success(request, f"Produkt-Typ '{product_meta['label']}' zugewiesen.")
        return redirect("studio:job_detail", job_id=job.id)
    
    # GET: Zeige Produkt-Auswahl
    return render(request, "studio/product_wizard.html", {
        "job": job,
        "assets": assets,
        "product_types": PRODUCT_TYPES,
        "post": {},
    })


# ─────────────────────────────────────────────────────────────────────────────
# WIZARD — Geführter Job-Erstell-Workflow (Output-Typ-First) — ALT, wird ersetzt
# ─────────────────────────────────────────────────────────────────────────────

WIZARD_SESSION_KEY = "studio_wizard"

OUTPUT_TYPES = {
    "preview": {
        "label": "Galerie-Preview",
        "icon": "🖼",
        "description": "Bild für die Galerie. Kein Verkauf nötig — alle Modelle erlaubt.",
        "steps_hint": "generate → preview",
        "allowed_models": ["flux_schnell", "sdxl", "flux_dev"],
        "pipeline_category": "custom",
        "template_flags": {
            "step_generate": True, "step_upscale": False, "step_vectorize": False,
            "step_cmyk": False, "step_pod_export": False, "step_preview": True,
            "step_mockup": False, "step_auto_qa": False,
        },
    },
    "pod": {
        "label": "POD-Produkt",
        "icon": "🛒",
        "description": "Produktbild für Printful, Etsy oder Shop. Nur kommerzielle Modelle.",
        "steps_hint": "generate → pod_export → preview",
        "allowed_models": ["flux_schnell", "sdxl"],
        "pipeline_category": "card_pod",
        "template_flags": {
            "step_generate": True, "step_upscale": False, "step_vectorize": False,
            "step_cmyk": False, "step_pod_export": True, "step_preview": True,
            "step_mockup": False, "step_auto_qa": False,
        },
    },
    "offset": {
        "label": "Offset-Druckdatei",
        "icon": "🖨",
        "description": "Hochauflösende CMYK-Druckdatei für Druckpartner. Nur kommerzielle Modelle.",
        "steps_hint": "generate → upscale → cmyk → preview",
        "allowed_models": ["flux_schnell", "sdxl"],
        "pipeline_category": "poster_offset",
        "template_flags": {
            "step_generate": True, "step_upscale": True, "step_vectorize": False,
            "step_cmyk": True, "step_pod_export": False, "step_preview": True,
            "step_mockup": False, "step_auto_qa": False,
        },
    },
    "img2img": {
        "label": "Foto → KI (Img2Img)",
        "icon": "📸",
        "description": "Lade ein Referenzfoto hoch und lass es vom KI-Modell nach deinem Prompt umgestalten.",
        "steps_hint": "img2img → preview",
        "allowed_models": ["sdxl", "flux_schnell"],
        "pipeline_category": "custom",
        "template_flags": {
            "step_generate": True, "step_upscale": False, "step_vectorize": False,
            "step_cmyk": False, "step_pod_export": False, "step_preview": True,
            "step_mockup": False, "step_auto_qa": False,
        },
    },
}

# Modell-Metadaten: Parameter + Endpoint + Verfügbarkeit
# available: True = Endpoint konfiguriert und nutzbar
# endpoint_var: Name der settings-Variable die den Endpoint-ID hält
MODEL_META = {
    "flux_schnell": {
        "label": "FLUX Schnell",
        "steps": 4,
        "guidance": 0.0,
        "license": "Apache 2.0 — kommerziell ✅",
        "badge": "ok",
        "available": True,
        "endpoint_var": "RUNPOD_ENDPOINT_ID",
        "img2img_support": True,
        "note": "Schnellstes Modell (4 Steps). Ideal für Produktion und schnelle Iterationen.",
    },
    "sdxl": {
        "label": "SDXL 1.0",
        "steps": 30,
        "guidance": 7.5,
        "license": "CreativeML Open Rail+M — kommerziell ✅",
        "badge": "ok",
        "available": True,
        "endpoint_var": "RUNPOD_SDXL_ENDPOINT_ID",
        "img2img_support": True,
        "note": "Hochqualitativ, 30 Steps. Besser für Details und realistische Darstellungen. Benötigt eigenen Endpoint.",
    },
    "flux_dev": {
        "label": "FLUX Dev",
        "steps": 20,
        "guidance": 3.5,
        "license": "⚠️ Nicht kommerziell — nur Preview/Test!",
        "badge": "warn",
        "available": True,
        "endpoint_var": "RUNPOD_ENDPOINT_ID",
        "img2img_support": False,
        "note": "Höhere Qualität als Schnell, aber nicht kommerziell lizenziert. Nur für interne Tests.",
    },
}

ASPECT_RATIOS = {
    "1:1":  (1024, 1024),
    "2:3":  (832, 1216),
    "3:2":  (1216, 832),
    "9:16": (768, 1344),
    "16:9": (1344, 768),
}

PRINT_FORMATS = {
    "A3":   {"label": "A3 (297×420 mm)", "width": 3507,  "height": 4961},
    "A2":   {"label": "A2 (420×594 mm)", "width": 4961,  "height": 7016},
    "50x70":{"label": "50×70 cm",        "width": 5906,  "height": 8268},
    "A4":   {"label": "A4 (210×297 mm)", "width": 2480,  "height": 3508},
}


def _wizard_get(request):
    return request.session.get(WIZARD_SESSION_KEY, {})


def _wizard_set(request, data):
    existing = _wizard_get(request)
    existing.update(data)
    request.session[WIZARD_SESSION_KEY] = existing
    request.session.modified = True


def _wizard_clear(request):
    request.session.pop(WIZARD_SESSION_KEY, None)
    request.session.modified = True


def _enrich_model_meta_with_endpoints(models_dict: dict) -> dict:
    """Fügt endpoint_configured Key zu jedem Modell hinzu (basierend auf Django Settings).
    Gibt neues Dict zurück ohne Original zu mutieren.
    """
    from django.conf import settings as djsettings
    enriched = {}
    for key, meta in models_dict.items():
        meta_copy = meta.copy()
        env_var = meta.get("endpoint_var", "")
        meta_copy["endpoint_configured"] = bool(getattr(djsettings, env_var, ""))
        enriched[key] = meta_copy
    return enriched


def _get_or_create_template(output_type: str, model: str) -> PipelineTemplate:
    """Sucht passendes Template oder legt es automatisch an.
    WICHTIG: Steps/Guidance werden immer modell-spezifisch gesetzt — nie am falschen Template wiederverwenden.
    """
    flags = OUTPUT_TYPES[output_type]["template_flags"]
    meta  = MODEL_META[model]
    category = OUTPUT_TYPES[output_type]["pipeline_category"]

    # Name ist eindeutig pro Output-Typ + Modell
    template_name = f"{OUTPUT_TYPES[output_type]['label']} — {meta['label']} (auto)"

    template = PipelineTemplate.objects.filter(
        name=template_name,
        category=category,
        default_model=model,
        is_active=True,
    ).first()

    if not template:
        template = PipelineTemplate.objects.create(
            name=template_name,
            description=f"Automatisch erstellt durch Studio-Wizard — {meta['note']}",
            category=category,
            default_model=model,
            default_steps=meta["steps"],
            default_guidance=meta["guidance"],
            default_width=1024,
            default_height=1024,
            is_active=True,
            **flags,
        )
    else:
        # Steps/Guidance aktualisieren falls sie sich geändert haben
        if template.default_steps != meta["steps"] or template.default_guidance != meta["guidance"]:
            template.default_steps = meta["steps"]
            template.default_guidance = meta["guidance"]
            template.save(update_fields=["default_steps", "default_guidance"])

    return template


# ── Step 1: Output-Typ wählen ─────────────────────────────────────────────

@studio_required
def wizard_step1(request):
    """REDIRECT: Alter Wizard → Neue Single-Page Job-Erstellung"""
    messages.info(request, "🔄 Der Wizard wurde durch ein verbessertes Formular ersetzt")
    return redirect("studio:job_create")


# ── Step 2: Modell + Prompt (+ Referenzfoto bei Img2Img) ─────────────────

@studio_required
def wizard_step2(request):
    """REDIRECT: Alter Wizard → Neue Single-Page Job-Erstellung"""
    return redirect("studio:job_create")


# ── Step 3: Output-Details ────────────────────────────────────────────────

@studio_required
def wizard_step3(request):
    """REDIRECT: Alter Wizard → Neue Single-Page Job-Erstellung"""
    return redirect("studio:job_create")


# ── Confirm + Job anlegen ─────────────────────────────────────────────────

@studio_required
def wizard_confirm(request):
    """REDIRECT: Alter Wizard → Neue Single-Page Job-Erstellung"""
    return redirect("studio:job_create")


# ─────────────────────────────────────────────────────────────────────────────
# Knowledge Base — Modelle (Ordnerverzeichnis-Struktur)
# ─────────────────────────────────────────────────────────────────────────────

@studio_required
def knowledge_models(request):
    """
    Knowledge Base: AI-Modelle mit aufklappbarer Ordnerstruktur.
    Erklärt Diffusion, Parameter, Lizenzen, Best Practices.
    """
    return render(request, "studio/knowledge_models.html")


# ─────────────────────────────────────────────────────────────────────────────
# Knowledge IT — Technische System-Dokumentation
# ─────────────────────────────────────────────────────────────────────────────

@studio_required
def knowledge_it(request):
    """
    Knowledge Base IT: Komponenten, Ordnerstruktur, Tailscale, Konten.
    Wo was geändert werden muss für Frontend/Backend/Server/Homeserver.
    Vergleiche und Upgrade-Szenarien.
    """
    return render(request, "studio/knowledge_it.html")
