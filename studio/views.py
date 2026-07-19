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
    templates = PipelineTemplate.objects.filter(is_active=True).order_by("name")
    prompt_templates = PromptTemplate.objects.filter(is_public=True).order_by("category", "title")
    # Projekte immer laden — wird in allen Returns benötigt
    projects = Project.objects.filter(
        models.Q(created_by=request.user) | models.Q(team_members=request.user)
    ).distinct().order_by('title')

    if request.method == "POST":
        title          = request.POST.get("title", "").strip()
        template_id    = request.POST.get("pipeline_template", "").strip()
        prompt         = request.POST.get("prompt", "").strip()
        negative_prompt = request.POST.get("negative_prompt", "").strip()
        notes          = request.POST.get("notes", "").strip()
        model          = request.POST.get("model", "").strip()

        # Optionale Override-Felder (leer = None = Template-Default)
        width      = request.POST.get("width") or None
        height     = request.POST.get("height") or None
        steps      = request.POST.get("steps") or None
        guidance   = request.POST.get("guidance") or None
        seed       = request.POST.get("seed") or None
        num_images = int(request.POST.get("num_images") or 1)

        errors = []
        if not title:      errors.append("Titel ist erforderlich.")
        if not template_id: errors.append("Pipeline-Template ist erforderlich.")
        if not prompt:     errors.append("Prompt ist erforderlich.")

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, "studio/job_create.html", {
                "templates": templates,
                "prompt_templates": prompt_templates,
                "projects": projects,
                "post": request.POST,
            })

        try:
            template = PipelineTemplate.objects.get(id=template_id, is_active=True)
        except PipelineTemplate.DoesNotExist:
            messages.error(request, "Template nicht gefunden.")
            return render(request, "studio/job_create.html", {
                "templates": templates,
                "prompt_templates": prompt_templates,
                "projects": projects,
                "post": request.POST,
            })

        project_id = request.POST.get('project_id', '').strip()
        project = None
        if project_id:
            try:
                project = Project.objects.get(id=project_id)
            except Project.DoesNotExist:
                pass

        job = Job.objects.create(
            title=title,
            pipeline_template=template,
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

        messages.success(request, f"Job '{job.title}' angelegt. Admin muss ihn starten.")
        return redirect("studio:job_detail", job_id=job.id)

    return render(request, 'studio/job_create.html', {
        'templates': templates,
        'prompt_templates': prompt_templates,
        'projects': projects,
        'post': {},
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

    assets = []
    for step in preview_steps:
        filename = f"{step.output_asset_id}_preview.jpg"
        filepath = preview_dir / filename
        try:
            file_exists = filepath.exists()
        except (PermissionError, OSError):
            file_exists = True  # NAS nicht lesbar für www-data — trotzdem anzeigen, Nginx serviert es
        assets.append({
            "asset_id": str(step.output_asset_id),
            "filename": filename,
            "exists": file_exists,
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

    gallery_image = GalleryImage.objects.create(
        title=title,
        slug=slug,
        category=category,
        cta_type=cta_type,
        file_path=f"exports/preview/{preview_filename}",
        thumb_path=f"exports/preview/{preview_filename}",  # Preview ist bereits klein — kein Pillow-Open auf NAS
        is_public=False,  # Admin gibt explizit frei
        source_job_id=job.id,
        project=job.project,  # Projekt vom Job erben
    )

    try:
        generate_all_mockups.delay(str(gallery_image.id))
    except Exception as exc:
        logger.warning("[asset_select] generate_all_mockups.delay fehlgeschlagen: %s", exc)

    logger.info(
        "[asset_select] GalleryImage %s von User %s (Job %s)",
        gallery_image.id, request.user.username, job_id,
    )
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
# WIZARD — Geführter Job-Erstell-Workflow (Output-Typ-First)
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
}

MODEL_META = {
    "flux_schnell": {"label": "FLUX Schnell", "steps": 4,  "guidance": 0,   "license": "Apache 2.0 — kommerziell ✅", "badge": "ok"},
    "sdxl":         {"label": "SDXL",         "steps": 30, "guidance": 7.5, "license": "CreativeML Open Rail+M — kommerziell ✅", "badge": "ok"},
    "flux_dev":     {"label": "FLUX Dev",      "steps": 20, "guidance": 3.5, "license": "⚠️ Nicht kommerziell — nur Preview/Test!", "badge": "warn"},
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


def _get_or_create_template(output_type: str, model: str) -> PipelineTemplate:
    """Sucht passendes Template oder legt es automatisch an."""
    flags = OUTPUT_TYPES[output_type]["template_flags"]
    meta  = MODEL_META[model]
    category = OUTPUT_TYPES[output_type]["pipeline_category"]

    template = PipelineTemplate.objects.filter(
        category=category,
        default_model=model,
        is_active=True,
        **flags,
    ).first()

    if not template:
        template = PipelineTemplate.objects.create(
            name=f"{OUTPUT_TYPES[output_type]['label']} — {meta['label']} (auto)",
            description="Automatisch erstellt durch Studio-Wizard",
            category=category,
            default_model=model,
            default_steps=meta["steps"],
            default_guidance=meta["guidance"],
            default_width=1024,
            default_height=1024,
            is_active=True,
            **flags,
        )
    return template


# ── Step 1: Output-Typ wählen ─────────────────────────────────────────────

@studio_required
def wizard_step1(request):
    if request.method == "POST":
        output_type = request.POST.get("output_type")
        if output_type not in OUTPUT_TYPES:
            messages.error(request, "Bitte einen Output-Typ wählen.")
            return redirect("studio:wizard_step1")
        _wizard_set(request, {"output_type": output_type})
        return redirect("studio:wizard_step2")

    _wizard_clear(request)
    return render(request, "studio/wizard/step1.html", {
        "output_types": OUTPUT_TYPES,
    })


# ── Step 2: Modell + Prompt ───────────────────────────────────────────────

@studio_required
def wizard_step2(request):
    wizard = _wizard_get(request)
    if not wizard.get("output_type"):
        return redirect("studio:wizard_step1")

    output_type = wizard["output_type"]
    otype_meta  = OUTPUT_TYPES[output_type]
    allowed     = {k: MODEL_META[k] for k in otype_meta["allowed_models"]}
    prompts     = PromptTemplate.objects.filter(is_public=True).order_by("category", "title")

    if request.method == "POST":
        model          = request.POST.get("model", "").strip()
        prompt         = request.POST.get("prompt", "").strip()
        negative_prompt = request.POST.get("negative_prompt", "").strip()
        num_images     = int(request.POST.get("num_images") or 1)
        seed           = request.POST.get("seed") or None

        errors = []
        if model not in allowed:
            errors.append("Bitte ein Modell wählen.")
        if not prompt:
            errors.append("Prompt ist erforderlich.")

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, "studio/wizard/step2.html", {
                "output_type": output_type, "otype_meta": otype_meta,
                "allowed_models": allowed, "prompts": prompts, "post": request.POST,
            })

        _wizard_set(request, {
            "model": model,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "num_images": num_images,
            "seed": int(seed) if seed else None,
        })
        return redirect("studio:wizard_step3")

    return render(request, "studio/wizard/step2.html", {
        "output_type": output_type,
        "otype_meta": otype_meta,
        "allowed_models": allowed,
        "prompts": prompts,
        "post": wizard,
    })


# ── Step 3: Output-Details ────────────────────────────────────────────────

@studio_required
def wizard_step3(request):
    wizard = _wizard_get(request)
    if not wizard.get("model"):
        return redirect("studio:wizard_step2")

    output_type = wizard["output_type"]
    otype_meta  = OUTPUT_TYPES[output_type]

    # Kontext für POD: verfügbare Produkte + Sales-Channels
    from shop.models import Product
    from channels.models import SalesChannel
    products  = Product.objects.filter(is_active=True).order_by("name") if output_type == "pod" else []
    channels  = SalesChannel.objects.filter(is_active=True).order_by("name")

    if request.method == "POST":
        details = {}

        if output_type == "preview":
            details["aspect_ratio"] = request.POST.get("aspect_ratio", "1:1")
            details["category"]     = request.POST.get("category", "art")
            details["tags"]         = request.POST.get("tags", "").strip()

        elif output_type == "pod":
            product_id = request.POST.get("product_id", "").strip()
            if not product_id:
                messages.error(request, "Bitte ein Produkt wählen.")
                return render(request, "studio/wizard/step3.html", {
                    "output_type": output_type, "otype_meta": otype_meta,
                    "products": products, "channels": channels,
                    "aspect_ratios": ASPECT_RATIOS, "post": request.POST,
                })
            details["product_id"]  = product_id
            details["aspect_ratio"] = request.POST.get("aspect_ratio", "1:1")
            details["channel_id"]  = request.POST.get("channel_id", "")

        elif output_type == "offset":
            details["print_format"]  = request.POST.get("print_format", "A3")
            details["dpi"]           = int(request.POST.get("dpi") or 300)
            details["bleed_mm"]      = int(request.POST.get("bleed_mm") or 3)
            details["channel_id"]    = request.POST.get("channel_id", "")

        _wizard_set(request, {"details": details})
        return redirect("studio:wizard_confirm")

    return render(request, "studio/wizard/step3.html", {
        "output_type": output_type,
        "otype_meta": otype_meta,
        "products": products,
        "channels": channels,
        "aspect_ratios": ASPECT_RATIOS,
        "print_formats": PRINT_FORMATS,
        "post": wizard.get("details", {}),
    })


# ── Confirm + Job anlegen ─────────────────────────────────────────────────

@studio_required
def wizard_confirm(request):
    wizard = _wizard_get(request)
    if not wizard.get("details") is not None and not wizard.get("output_type"):
        return redirect("studio:wizard_step1")

    output_type = wizard["output_type"]
    model       = wizard["model"]
    details     = wizard.get("details", {})

    # Größe aus Seitenverhältnis / Druckformat ableiten
    if output_type == "offset":
        fmt = PRINT_FORMATS.get(details.get("print_format", "A3"), PRINT_FORMATS["A3"])
        width, height = fmt["width"], fmt["height"]
    else:
        ratio = details.get("aspect_ratio", "1:1")
        width, height = ASPECT_RATIOS.get(ratio, (1024, 1024))

    # Projekte für Auswahl in Confirm-Form
    user_projects = Project.objects.filter(
        models.Q(created_by=request.user) | models.Q(team_members=request.user)
    ).distinct().order_by('title')

    def _get_default_project():
        """'Allgemein'-Projekt als Fallback — wird in Data-Migration erstellt."""
        return Project.objects.filter(slug='allgemein').first()

    if request.method == "POST":
        title = request.POST.get("title", f"{OUTPUT_TYPES[output_type]['label']} — {wizard['prompt'][:40]}").strip()

        # Projekt zuordnen — Auswahl oder "Allgemein" als Default
        project_id = request.POST.get("project_id", "").strip()
        project = None
        if project_id:
            try:
                project = Project.objects.get(id=project_id)
            except Project.DoesNotExist:
                pass
        if project is None:
            project = _get_default_project()

        try:
            template = _get_or_create_template(output_type, model)
        except Exception as exc:
            messages.error(request, f"Template-Fehler: {exc}")
            return redirect("studio:wizard_step1")

        notes_parts = []
        if details.get("tags"):        notes_parts.append(f"Tags: {details['tags']}")
        if details.get("product_id"):  notes_parts.append(f"Produkt-ID: {details['product_id']}")
        if details.get("channel_id"):  notes_parts.append(f"Channel-ID: {details['channel_id']}")
        if details.get("print_format"):notes_parts.append(f"Format: {details['print_format']}, {details.get('dpi')}dpi, Bleed {details.get('bleed_mm')}mm")

        meta = MODEL_META[model]
        job = Job.objects.create(
            title=title,
            pipeline_template=template,
            project=project,
            prompt=wizard["prompt"],
            negative_prompt=wizard.get("negative_prompt", ""),
            model=model,
            width=width,
            height=height,
            num_steps=meta["steps"],
            guidance=meta["guidance"],
            num_images=wizard.get("num_images", 1),
            seed=wizard.get("seed"),
            notes="\n".join(notes_parts),
            status="draft",
            created_by=request.user,
        )

        _wizard_clear(request)
        messages.success(request, f"Job '{job.title}' angelegt. Admin muss ihn starten.")
        return redirect("studio:job_detail", job_id=job.id)

    return render(request, "studio/wizard/confirm.html", {
        "wizard": wizard,
        "output_type": output_type,
        "otype_meta": OUTPUT_TYPES[output_type],
        "model_meta": MODEL_META[model],
        "width": width,
        "height": height,
        "details": details,
        "user_projects": user_projects,
        "default_project": _get_default_project(),
    })


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
