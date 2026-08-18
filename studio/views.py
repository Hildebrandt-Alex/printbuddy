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
    VEREINFACHTER WIZARD: Nur FLUX Schnell für Bildgenerierung
    3 Schritte: Medientyp → Modell → Parameter
    """
    prompt_templates = PromptTemplate.objects.filter(is_public=True).order_by("category", "title")
    
    # Superuser/Staff sehen ALLE Projekte, normale User nur eigene
    if request.user.is_superuser or request.user.is_staff:
        projects = Project.objects.filter(is_active=True).order_by('-updated_at', 'title')
    else:
        projects = Project.objects.filter(
            models.Q(created_by=request.user) | models.Q(team_members=request.user),
            is_active=True
        ).distinct().order_by('-updated_at', 'title')

    if request.method == "POST":
        title           = request.POST.get("title", "").strip()
        prompt          = request.POST.get("prompt", "").strip()
        negative_prompt = request.POST.get("negative_prompt", "").strip()
        model           = request.POST.get("model", "flux_schnell")  # Default
        pipeline_mode   = request.POST.get("pipeline_mode", "text2img")
        seed            = request.POST.get("seed") or None
        num_images      = int(request.POST.get("num_images") or 1)
        img2img_strength = request.POST.get("img2img_strength")
        reference_image = request.FILES.get("reference_image")
        face_image      = request.FILES.get("face_image")

        errors = []
        if not title:  errors.append("Titel ist erforderlich.")
        if not prompt: errors.append("Prompt ist erforderlich.")
        if pipeline_mode == "img2img" and not reference_image:
            errors.append("Referenzbild ist erforderlich für Bild→Bild Modus.")
        if pipeline_mode == "face_swap" and not face_image:
            errors.append("Portrait ist erforderlich für Face Swap Modus.")

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, "studio/job_create.html", {
                "prompt_templates": prompt_templates,
                "projects": projects,
                "post": request.POST,
            })

        # Projekt-Zuordnung (optional)
        project_id = request.POST.get('project_id', '').strip()
        project = None
        if project_id:
            try:
                project = Project.objects.get(id=project_id)
            except Project.DoesNotExist:
                pass

        # Pipeline Template basierend auf Modus wählen
        if pipeline_mode == "face_swap":
            # Suche nach Face Swap Template (falls vorhanden)
            pipeline_template = PipelineTemplate.objects.filter(
                is_active=True, 
                step_face_swap=True
            ).first()
            if not pipeline_template:
                # Fallback: Preview Only Template
                pipeline_template = PipelineTemplate.objects.filter(
                    is_active=True,
                    step_upscale=False
                ).first()
        else:
            # Preview Only Template (kein Upscale für schnelle Iteration)
            pipeline_template = PipelineTemplate.objects.filter(
                is_active=True,
                step_upscale=False
            ).first()
        
        if not pipeline_template:
            # Fallback: erstes aktives Template
            pipeline_template = PipelineTemplate.objects.filter(is_active=True).first()
        
        if not pipeline_template:
            messages.error(
                request, 
                "Kein aktives Pipeline-Template gefunden. Admin muss ein Template anlegen."
            )
            return render(request, "studio/job_create.html", {
                "prompt_templates": prompt_templates,
                "projects": projects,
                "post": request.POST,
            })
        
        # Param Notes für img2img strength (Backend liest dies aus)
        notes = f"PipelineMode: {pipeline_mode}"
        if img2img_strength:
            notes += f"\nImg2Img: {img2img_strength}"
        
        # Job erstellen mit Template
        job = Job.objects.create(
            title=title,
            pipeline_template=pipeline_template,
            project=project,
            prompt=prompt,
            negative_prompt=negative_prompt,
            reference_image=reference_image,
            face_image=face_image,
            model=model,
            width=1024,        # FLUX Schnell Standard
            height=1024,
            num_steps=4 if model == "flux_schnell" else (20 if model == "flux_dev" else 30),
            guidance=7.0,
            seed=int(seed) if seed else None,
            num_images=num_images,
            notes=notes,
            status='draft',
            created_by=request.user,
        )

        messages.success(request, f"Job '{job.title}' erstellt. Admin muss ihn starten.")
        return redirect("studio:job_detail", job_id=job.id)

    return render(request, 'studio/job_create.html', {
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


@require_POST
@studio_required
def cancel_job(request, job_id):
    """Cancel a queued or running job."""
    job = get_object_or_404(Job, id=job_id, created_by=request.user)
    
    # Nur Jobs in queued/running können gecancelt werden
    if job.status not in ['queued', 'running']:
        messages.error(request, f"Job kann nicht gestoppt werden (Status: {job.get_status_display()})")
        return redirect('studio:job_detail', job_id=job.id)
    
    # Job Status auf cancelled setzen
    job.status = 'cancelled'
    job.save()
    
    # Alle pending/running Steps auf skipped setzen
    job.steps.filter(status__in=['pending', 'running']).update(status='skipped')
    
    messages.success(request, f'Job "{job.title}" wurde gestoppt.')
    return redirect('studio:job_list')


# ─────────────────────────────────────────────────────────────────────────────
# Job-Ergebnisse
# ─────────────────────────────────────────────────────────────────────────────

@studio_required
def job_results(request, job_id):
    job = get_object_or_404(Job, id=job_id, created_by=request.user)

    if job.status != "done":
        messages.warning(request, "Job ist noch nicht abgeschlossen.")
        return redirect("studio:job_detail", job_id=job.id)

    # Job-basierte Pfad-Struktur
    base = Path(getattr(settings, "NAS_BASE_PATH", "local_nas"))
    job_base = base / "jobs" / str(job.id)
    
    original_dir = job_base / "original"
    adjusted_dir = job_base / "adjusted"
    crop_dir = job_base / "crop"
    preview_dir = job_base / "exports" / "preview"
    
    # Prüfe welche Assets bereits als GalleryImage vorgemerkt sind
    from gallery.models import GalleryImage
    existing_gallery_images = list(GalleryImage.objects.filter(source_job_id=job.id))

    assets = []
    
    # ═══════════════════════════════════════════════════════════════════
    # 1. ORIGINAL: Generate oder Upscale (nur der neueste)
    # ═══════════════════════════════════════════════════════════════════
    original_step = None
    for step_type in ['upscale', 'generate']:
        try:
            original_step = job.steps.get(step_type=step_type, status='done')
            break
        except job.steps.model.DoesNotExist:
            continue
    
    if original_step and original_step.output_asset_id:
        asset_id = str(original_step.output_asset_id)
        
        # Upscale hat _4x Suffix, Generate ohne
        if original_step.step_type == "upscale":
            filename = f"{asset_id}_4x.png"
        else:
            filename = f"{asset_id}.png"
        
        filepath = original_dir / filename
        
        try:
            file_exists = filepath.exists()
        except (PermissionError, OSError):
            file_exists = True  # NAS nicht lesbar - Nginx serviert es trotzdem
        
        # Gallery Status Check
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
            "directory": f"jobs/{job.id}/original",
            "exists": file_exists,
            "gallery_status": status,
            "gallery_status_label": status_label,
            "asset_type": "🖼️ Original" if original_step.step_type == "generate" else "⬆️ Upscaled",
        })
    
    # ═══════════════════════════════════════════════════════════════════
    # 2. ENHANCEMENT JOBS: Wenn kein Original → Zeige Preview-Exports
    # ═══════════════════════════════════════════════════════════════════
    if not original_step:
        # Enhancement Jobs haben keine generate/upscale → zeige Preview-Exports
        preview_steps = job.steps.filter(step_type="preview_export", status="done")
        for step in preview_steps:
            if not step.output_asset_id:
                continue
            
            asset_id = str(step.output_asset_id)
            filename = f"{asset_id}_preview.jpg"
            filepath = preview_dir / filename
            
            try:
                file_exists = filepath.exists()
            except (PermissionError, OSError):
                file_exists = True
            
            # Gallery Status Check
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
                "directory": f"jobs/{job.id}/exports/preview",
                "exists": file_exists,
                "gallery_status": status,
                "gallery_status_label": status_label,
                "asset_type": "📦 Enhancement Export",
            })
    
    # ═══════════════════════════════════════════════════════════════════
    # 3. ADJUSTMENTS: Quick Adjust & Crop (chronologisch)
    # ═══════════════════════════════════════════════════════════════════
    adjustment_steps = job.steps.filter(
        step_type__in=["quick_adjust", "crop"],
        status__in=["pending", "running", "done"]
    ).order_by('id')  # Chronologisch (älteste zuerst)
    
    adjust_counter = 0
    crop_counter = 0
    
    for step in adjustment_steps:
        # Pending/running steps haben noch kein output_asset_id
        if not step.output_asset_id:
            assets.append({
                "asset_id": None,
                "filename": None,
                "directory": None,
                "exists": False,
                "gallery_status": "processing",
                "gallery_status_label": "⏳ Wird verarbeitet...",
                "asset_type": "🎨 Quick Adjust" if step.step_type == "quick_adjust" else "✂️ Crop",
                "is_processing": True,
                "step_status": step.status,
            })
            continue
        
        asset_id = str(step.output_asset_id)
        
        if step.step_type == "quick_adjust":
            adjust_counter += 1
            
            # ROBUST: Suche mit Glob-Pattern (Timestamp kann abweichen)
            import glob
            pattern = str(adjusted_dir / f"{asset_id}_adjusted_*.png")
            matching_files = glob.glob(pattern)
            
            if matching_files:
                # Neueste Version
                filepath = Path(max(matching_files, key=lambda p: Path(p).stat().st_mtime))
                filename = filepath.name
            else:
                # Fallback
                filename = f"{asset_id}_adjusted.png"
                filepath = adjusted_dir / filename
            
            asset_type = f"🎨 Adjusted #{adjust_counter}"
            directory = f"jobs/{job.id}/adjusted"
            
        elif step.step_type == "crop":
            crop_counter += 1
            filename = f"{asset_id}_cropped.png"
            filepath = crop_dir / filename
            asset_type = f"✂️ Cropped #{crop_counter}"
            directory = f"jobs/{job.id}/crop"
        
        try:
            file_exists = filepath.exists()
        except (PermissionError, OSError):
            file_exists = True
        
        # Gallery Status Check
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
            "directory": directory,
            "exists": file_exists,
            "gallery_status": status,
            "gallery_status_label": status_label,
            "asset_type": asset_type,
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

    # Job-basierte Pfade
    base = Path(getattr(settings, "NAS_BASE_PATH", "local_nas"))
    preview_dir = base / "jobs" / str(job.id) / "exports" / "preview"
    
    # ROBUST: Suche nach passender Preview-Datei (generate/upscale vs. preview_export haben unterschiedliche IDs)
    preview_candidates = [
        f"{asset_id}_preview.jpg",  # Exakte Übereinstimmung
    ]
    
    # Fallback: Alle Preview-Dateien im Ordner durchsuchen
    import glob
    try:
        all_previews = glob.glob(str(preview_dir / "*_preview.jpg"))
        if all_previews:
            # Neueste Preview-Datei (falls mehrere)
            preview_src = Path(max(all_previews, key=lambda p: Path(p).stat().st_mtime))
            preview_filename = preview_src.name
        else:
            # Keine Preview gefunden → Fehlermeldung
            messages.error(request, f"Keine Preview-Datei für Job {job.id} gefunden.")
            return redirect("studio:job_results", job_id=job.id)
    except (PermissionError, OSError) as exc:
        # NAS nicht lesbar — verwende exakte asset_id (Nginx kann es evtl. trotzdem servieren)
        logger.warning("[asset_select] NAS preview_dir nicht lesbar: %s", exc)
        preview_filename = f"{asset_id}_preview.jpg"
        preview_src = preview_dir / preview_filename

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
            file_path=f"jobs/{job.id}/exports/preview/{preview_filename}",
            thumb_path=f"jobs/{job.id}/exports/preview/{preview_filename}",  # Preview ist bereits klein — kein Pillow-Open auf NAS
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
    
    # Asset-Previews sammeln (job-basiert)
    from pathlib import Path
    base = Path(getattr(settings, "NAS_BASE_PATH", "local_nas"))
    preview_dir = base / "jobs" / str(job.id) / "exports" / "preview"
    
    assets = []
    for step in preview_steps:
        asset_id = str(step.output_asset_id)
        filename = f"{asset_id}_preview.jpg"
        assets.append({
            "asset_id": asset_id,
            "filename": filename,
            "url": f"/media/jobs/{job.id}/exports/preview/{filename}",
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


# ─────────────────────────────────────────────────────────────────────────────
# Enhancement Job Creation — Auto-Approved
# ─────────────────────────────────────────────────────────────────────────────

@studio_required
@require_POST
def create_enhancement_job(request, job_id):
    """
    Erstellt Enhancement-Job basierend auf Original-Job.
    Enhancement-Jobs werden AUTOMATISCH approved (status='queued').
    Nutzt existierendes Preview-Asset als Input (keine Neugenerierung).
    """
    import json
    from django.utils import timezone
    from jobs.services import build_pipeline_chain
    from jobs.models import JobStep
    
    original_job = get_object_or_404(Job, id=job_id)
    
    # Validierung: Nur von fertigen Jobs
    if original_job.status != 'done':
        messages.error(request, "Enhancement nur für abgeschlossene Jobs möglich.")
        return redirect('studio:job_results', job_id=job_id)
    
    # Validierung: Mindestens ein Step ausgewählt
    selected_steps = request.POST.getlist('steps')
    if not selected_steps:
        messages.error(request, "Bitte mindestens einen Enhancement-Schritt auswählen.")
        return redirect('studio:job_results', job_id=job_id)
    
    # Source Asset Selection (User-wählbar via POST)
    source_asset_id = request.POST.get('source_asset')
    
    if not source_asset_id:
        # Fallback: Letztes Asset (beliebiger Typ)
        try:
            last_step = JobStep.objects.filter(
                job=original_job,
                step_type__in=["preview_export", "quick_adjust", "crop"],
                status="done"
            ).exclude(output_asset_id__isnull=True).order_by('-completed_at').first()
            
            if not last_step:
                messages.error(request, "Kein Asset gefunden für Enhancement.")
                return redirect('studio:job_results', job_id=job_id)
            
            source_asset_id = str(last_step.output_asset_id)
            logger.info(f"[Enhancement] Fallback zu letztem Asset: {source_asset_id}")
        except Exception as e:
            logger.error(f"[create_enhancement_job] Fehler: {e}")
            messages.error(request, "Fehler beim Laden des Assets.")
            return redirect('studio:job_results', job_id=job_id)
    
    # Validierung: Asset existiert und ist done
    source_step = JobStep.objects.filter(
        job=original_job,
        output_asset_id=source_asset_id,
        status="done"
    ).first()
    
    if not source_step:
        messages.error(request, "Gewähltes Asset nicht gefunden.")
        return redirect('studio:job_results', job_id=job_id)
    
    logger.info(f"[Enhancement] Verwende {source_step.step_type} Asset: {source_asset_id}")
    
    # Enhancement-Only Template finden (robust via semantic field)
    enhancement_template = PipelineTemplate.objects.filter(
        step_generate=False,
        is_active=True
    ).first()
    
    if not enhancement_template:
        messages.error(
            request, 
            "Enhancement-Template nicht gefunden. Bitte 'python create_enhancement_template.py' ausführen."
        )
        return redirect('studio:job_results', job_id=job_id)
    
    # Notes mit source_job_id, source_asset_id und gewählten Steps
    notes_data = {
        "source_job_id": str(original_job.id),
        "source_asset_id": source_asset_id,
        "enhancement_steps": selected_steps,
        "is_enhancement": True
    }
    
    # Job erstellen — AUTOMATISCH approved (status='queued')
    enhancement_job = Job.objects.create(
        title=f"Enhancement: {original_job.title}",
        status='queued',  # ← DIREKT queued, NICHT draft!
        pipeline_template=enhancement_template,
        prompt=original_job.prompt,  # Original-Prompt übernehmen
        negative_prompt=original_job.negative_prompt,
        model=original_job.model,
        notes=json.dumps(notes_data),
        created_by=request.user,
        project=original_job.project,  # Projekt übernehmen
        started_at=timezone.now()
    )
    
    logger.info(
        f"[create_enhancement_job] Enhancement-Job {enhancement_job.id} erstellt "
        f"von {request.user.username} für Original-Job {original_job.id}"
    )
    
    # Celery Chain direkt starten
    try:
        task_chain = build_pipeline_chain(str(enhancement_job.id))
        result = task_chain.apply_async()
        enhancement_job.celery_chain_id = result.id
        enhancement_job.save(update_fields=['celery_chain_id'])
        
        messages.success(
            request, 
            f"✅ Enhancement-Job gestartet! ({len(selected_steps)} Schritte)"
        )
    except Exception as e:
        logger.error(f"[create_enhancement_job] Fehler beim Starten der Chain: {e}")
        enhancement_job.status = 'failed'
        enhancement_job.save(update_fields=['status'])
        messages.error(request, f"Fehler beim Starten: {e}")
    
    return redirect('studio:job_detail', job_id=enhancement_job.id)


# ─────────────────────────────────────────────────────────────────────────────
# Quick Adjust — Farb-/Helligkeits-/Crop-Anpassungen
# ─────────────────────────────────────────────────────────────────────────────

@studio_required
@require_POST
def quick_adjust_image(request, job_id):
    """
    Wendet Quick Adjustments auf das neueste Asset eines Jobs an.
    REFACTORED: Speichert DIREKT JPG Preview (kein async Celery Task mehr).
    
    Unterstützt:
    - Color adjustments (brightness, contrast, saturation, sharpness)
    - Crop (mit x, y, width, height)
    
    Erstellt einen neuen Job-Step mit den Anpassungsparametern.
    """
    import json
    import uuid
    from datetime import datetime
    from pathlib import Path
    from django.http import JsonResponse
    from jobs.models import JobStep
    from PIL import Image, ImageEnhance
    from django.conf import settings
    
    job = get_object_or_404(Job, id=job_id)
    
    # Validierung: Job muss done sein (Enhancement erstellt neue Jobs)
    if job.status != 'done':
        return JsonResponse({
            'success': False,
            'error': 'Job muss abgeschlossen sein für Quick Adjust.'
        }, status=400)
    
    # Anpassungstyp bestimmen
    adjust_type = request.POST.get('adjust_type', 'color')  # 'color' oder 'crop'
    
    if adjust_type == 'color':
        # Color Adjustment Parameter lesen
        try:
            brightness = int(request.POST.get('brightness', 0))
            contrast = int(request.POST.get('contrast', 0))
            saturation = int(request.POST.get('saturation', 0))
            sharpness = int(request.POST.get('sharpness', 100))
            
            # Validierung
            if not (-100 <= brightness <= 100):
                raise ValueError("Brightness muss zwischen -100 und 100 liegen")
            if not (-100 <= contrast <= 100):
                raise ValueError("Contrast muss zwischen -100 und 100 liegen")
            if not (-100 <= saturation <= 100):
                raise ValueError("Saturation muss zwischen -100 und 100 liegen")
            if not (0 <= sharpness <= 200):
                raise ValueError("Sharpness muss zwischen 0 und 200 liegen")
            
        except (ValueError, TypeError) as e:
            return JsonResponse({
                'success': False,
                'error': f'Ungültige Parameter: {e}'
            }, status=400)
        
        # Notes mit Quick Adjust Params erstellen/updaten
        try:
            notes_data = json.loads(job.notes) if job.notes else {}
        except json.JSONDecodeError:
            notes_data = {}
        
        notes_data['quick_adjust_params'] = {
            'brightness': brightness,
            'contrast': contrast,
            'saturation': saturation,
            'sharpness': sharpness
        }
        
        job.notes = json.dumps(notes_data)
        job.save(update_fields=['notes'])
        
        # ── Inline Processing (NO async Celery Task) ──
        try:
            # Source-Asset finden (prefer upscaled wenn vorhanden)
            nas_base = Path(getattr(settings, 'NAS_BASE_PATH', '/mnt/agency_nas'))
            job_dir = nas_base / 'jobs' / str(job.id)
            
            # Suche in dieser Reihenfolge: upscaled → original → adjusted
            source_path = None
            for subdir in ['original', 'adjusted']:
                if (job_dir / subdir).exists():
                    files = sorted((job_dir / subdir).glob('*_4x.png'), key=lambda p: p.stat().st_mtime, reverse=True)
                    if not files:  # kein 4x? dann alle PNGs
                        files = sorted((job_dir / subdir).glob('*.png'), key=lambda p: p.stat().st_mtime, reverse=True)
                    if files:
                        source_path = files[0]
                        break
            
            if not source_path or not source_path.exists():
                return JsonResponse({
                    'success': False,
                    'error': 'Kein Source-Asset gefunden'
                }, status=404)
            
            # Bild laden und anpassen
            img = Image.open(source_path)
            if img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGB')
            
            # Brightness (0.0 = schwarz, 1.0 = original, 2.0 = doppelt hell)
            if brightness != 0:
                factor = 1.0 + (brightness / 100.0)
                enhancer = ImageEnhance.Brightness(img)
                img = enhancer.enhance(max(0.0, factor))
            
            # Contrast
            if contrast != 0:
                factor = 1.0 + (contrast / 100.0)
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(max(0.0, factor))
            
            # Saturation
            if saturation != 0:
                factor = 1.0 + (saturation / 100.0)
                enhancer = ImageEnhance.Color(img)
                img = enhancer.enhance(max(0.0, factor))
            
            # Sharpness (0 → 0.0, 100 → 1.0, 200 → 2.0)
            if sharpness != 100:
                factor = sharpness / 100.0
                enhancer = ImageEnhance.Sharpness(img)
                img = enhancer.enhance(max(0.0, factor))
            
            # Speichere DIREKT als JPG Preview (kein PNG + async export)
            asset_id = uuid.uuid4()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Output in /jobs/{id}/exports/preview/ (direkt Web-ready)
            output_dir = job_dir / 'exports' / 'preview'
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{asset_id}_adjusted_{timestamp}.jpg"
            
            # JPG mit 90% Qualität (optimiert für Web/Studio)
            img.convert('RGB').save(output_path, 'JPEG', quality=90, optimize=True)
            
            # NFS-Permissions fix für Nginx-Zugriff
            import os
            os.chmod(output_path, 0o666)
            
            # JobStep erstellen (STATUS=DONE sofort, kein pending)
            step_order = job.steps.count() + 1
            job_step = JobStep.objects.create(
                job=job,
                step_type='quick_adjust',
                order=step_order,
                status='done',  # ← SOFORT done (nicht pending)
                output_asset_id=asset_id,
                params={
                    'brightness': brightness,
                    'contrast': contrast,
                    'saturation': saturation,
                    'sharpness': sharpness
                },
                completed_at=datetime.now()
            )
            
            logger.info(f"[quick_adjust_image] Adjusted JPG saved: {output_path} (JobStep {job_step.id})")
            
            return JsonResponse({
                'success': True,
                'step_id': str(job_step.id),
                'asset_id': str(asset_id),
                'filename': output_path.name,
                'message': 'Farbanpassung abgeschlossen!',
                'url': f'/media/jobs/{job.id}/exports/preview/{output_path.name}'
            })
            
        except Exception as e:
            logger.error(f"[quick_adjust_image] Fehler beim Processing: {e}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': f'Fehler beim Verarbeiten: {str(e)}'
            }, status=500)
    
    elif adjust_type == 'crop':
        # Crop Parameter lesen
        try:
            x = int(request.POST.get('x', 0))
            y = int(request.POST.get('y', 0))
            width = int(request.POST.get('width'))
            height = int(request.POST.get('height'))
            aspect_ratio = request.POST.get('aspect_ratio', 'free')
            
            # Validierung
            if width <= 0 or height <= 0:
                raise ValueError("Width/Height müssen positiv sein")
            if x < 0 or y < 0:
                raise ValueError("x/y müssen >= 0 sein")
            
        except (ValueError, TypeError) as e:
            return JsonResponse({
                'success': False,
                'error': f'Ungültige Crop-Parameter: {e}'
            }, status=400)
        
        # Notes mit Crop Params erstellen/updaten
        try:
            notes_data = json.loads(job.notes) if job.notes else {}
        except json.JSONDecodeError:
            notes_data = {}
        
        notes_data['crop_params'] = {
            'x': x,
            'y': y,
            'width': width,
            'height': height,
            'aspect_ratio': aspect_ratio
        }
        
        job.notes = json.dumps(notes_data)
        job.save(update_fields=['notes'])
        
        # JobStep erstellen
        step_order = job.steps.count() + 1
        job_step = JobStep.objects.create(
            job=job,
            step_type='crop',
            order=step_order,
            status='pending',
            params={
                'x': x,
                'y': y,
                'width': width,
                'height': height,
                'aspect_ratio': aspect_ratio
            }
        )
        
        # Celery Task starten
        try:
            result = crop_image.apply_async(args=[str(job_id)], queue='cpu_queue')
            logger.info(f"[quick_adjust_image] Crop task {result.id} gestartet für Job {job_id}")
            
            return JsonResponse({
                'success': True,
                'step_id': str(job_step.id),
                'task_id': result.id,
                'message': 'Crop wird verarbeitet...'
            })
        except Exception as e:
            logger.error(f"[quick_adjust_image] Fehler beim Starten der Crop-Task: {e}")
            job_step.status = 'failed'
            job_step.error_msg = str(e)
            job_step.save(update_fields=['status', 'error_msg'])
            return JsonResponse({
                'success': False,
                'error': f'Fehler beim Starten: {e}'
            }, status=500)
    
    else:
        return JsonResponse({
            'success': False,
            'error': f'Unbekannter adjust_type: {adjust_type}'
        }, status=400)
