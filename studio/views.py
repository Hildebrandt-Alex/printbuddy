import functools
import logging
import uuid as uuid_mod
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from jobs.models import Job, PipelineTemplate, PromptTemplate

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
# Job-Liste
# ─────────────────────────────────────────────────────────────────────────────

@studio_required
def job_list(request):
    status_filter = request.GET.get("status", "")
    jobs = (
        Job.objects.filter(created_by=request.user)
        .select_related("pipeline_template")
        .order_by("-created_at")
    )
    if status_filter:
        jobs = jobs.filter(status=status_filter)
    return render(request, "studio/job_list.html", {
        "jobs": jobs,
        "status_filter": status_filter,
        "status_choices": Job.JobStatus.choices,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Job anlegen (nur Draft — ADR-11)
# ─────────────────────────────────────────────────────────────────────────────

@studio_required
def job_create(request):
    templates = PipelineTemplate.objects.filter(is_active=True).order_by("name")
    prompt_templates = PromptTemplate.objects.filter(is_public=True).order_by("category", "title")

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
                "post": request.POST,
            })

        try:
            template = PipelineTemplate.objects.get(id=template_id, is_active=True)
        except PipelineTemplate.DoesNotExist:
            messages.error(request, "Template nicht gefunden.")
            return render(request, "studio/job_create.html", {
                "templates": templates,
                "prompt_templates": prompt_templates,
                "post": request.POST,
            })

        job = Job.objects.create(
            title=title,
            pipeline_template=template,
            prompt=prompt,
            negative_prompt=negative_prompt,
            notes=notes,
            model=model,
            width=int(width) if width else None,
            height=int(height) if height else None,
            steps=int(steps) if steps else None,
            guidance=float(guidance) if guidance else None,
            seed=int(seed) if seed else None,
            num_images=num_images,
            status="draft",
            created_by=request.user,
        )

        messages.success(request, f"Job '{job.title}' angelegt. Admin muss ihn starten.")
        return redirect("studio:job_detail", job_id=job.id)

    return render(request, "studio/job_create.html", {
        "templates": templates,
        "prompt_templates": prompt_templates,
        "post": {},
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
        assets.append({
            "asset_id": str(step.output_asset_id),
            "filename": filename,
            "exists": (preview_dir / filename).exists(),
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

    if not (preview_dir / preview_filename).exists():
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
        file_path=f"gallery/full/{preview_filename}",
        is_public=False,  # Admin gibt explizit frei
        source_job_id=job.id,
    )

    generate_all_mockups.delay(str(gallery_image.id))

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
