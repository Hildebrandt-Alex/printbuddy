import logging

from celery import chain
from django.utils import timezone

logger = logging.getLogger(__name__)


def build_pipeline_chain(job_id: str):
    """
    Baut die Celery-Task-Chain anhand des PipelineTemplates des Jobs.

    Reihenfolge (bindend laut ADR-03):
        generate_image
        → face_swap_image     (wenn step_face_swap UND reference_image vorhanden)
        → upscale_image       (wenn step_upscale)
        → vectorize_image     (wenn step_vectorize)
        → cmyk_export         (wenn step_cmyk)
        → pod_export          (wenn step_pod_export)
        → preview_export      (immer)
        → mockup_gen          (wenn step_mockup)
        → auto_qa             (wenn step_auto_qa)
        → notify_studio       (immer)

    Alle Tasks werden mit .si() (immutable) aufgerufen — kein State-Transfer.
    Nur UUIDs als Argumente — kein ORM-Objekt serialisieren.
    """
    from jobs.models import Job, JobStep
    from gpu.tasks import generate_image, upscale_image, face_swap_image
    from postprocess.tasks import (
        vectorize_image,
        cmyk_export,
        pod_export,
        preview_export,
        mockup_gen,
        auto_qa,
    )
    from jobs.tasks import notify_studio

    job = Job.objects.select_related("pipeline_template").get(id=job_id)
    t = job.pipeline_template

    # JobSteps anlegen (idempotent — löscht vorhandene und erstellt neu)
    JobStep.objects.filter(job_id=job_id).delete()

    step_definitions = []

    # Pflicht: generate
    step_definitions.append(("generate", True))
    
    # Face Swap NACH Generation, VOR Upscale (wenn aktiviert + reference_image vorhanden)
    if t.step_face_swap and job.reference_image:
        step_definitions.append(("face_swap", True))
        logger.info("[build_pipeline_chain] Face Swap aktiviert für Job %s", job_id)
    
    if t.step_upscale:
        step_definitions.append(("upscale", True))
    if t.step_vectorize:
        step_definitions.append(("vectorize", True))
    if t.step_cmyk:
        step_definitions.append(("cmyk_export", True))
    if t.step_pod_export:
        step_definitions.append(("pod_export", True))
    # Pflicht: preview (immer)
    step_definitions.append(("preview_export", True))
    if t.step_mockup:
        step_definitions.append(("mockup_gen", True))
    if t.step_auto_qa:
        step_definitions.append(("auto_qa", True))
    # Pflicht: notify
    step_definitions.append(("notify_studio_step", True))

    # JobStep-Objekte in DB anlegen
    for order, (step_type, _) in enumerate(step_definitions):
        # notify_studio_step wird als eigener Step-Typ gespeichert
        db_step_type = step_type if step_type != "notify_studio_step" else "notify_studio"
        JobStep.objects.create(
            job_id=job_id,
            step_type=db_step_type,
            order=order,
            status="pending",
        )

    logger.info("[build_pipeline_chain] %d Steps für Job %s angelegt", len(step_definitions), job_id)

    # Celery Chain aufbauen
    task_map = {
        "generate": generate_image.si(job_id),
        "face_swap": face_swap_image.si(job_id),
        "upscale": upscale_image.si(job_id),
        "vectorize": vectorize_image.si(job_id),
        "cmyk_export": cmyk_export.si(job_id),
        "pod_export": pod_export.si(job_id),
        "preview_export": preview_export.si(job_id),
        "mockup_gen": mockup_gen.si(job_id),
        "auto_qa": auto_qa.si(job_id),
        "notify_studio_step": notify_studio.si(job_id),
    }

    tasks = [task_map[step_type] for step_type, _ in step_definitions]
    pipeline = chain(*tasks)
    return pipeline


def start_job(job_id: str):
    """
    Startet einen Job: status draft → queued, Chain einreihen.
    Wird nur durch Admin-Action aufgerufen (ADR-11).
    """
    from jobs.models import Job

    job = Job.objects.get(id=job_id)

    if job.status != "draft":
        logger.warning("[start_job] Job %s hat Status %s — erwartet draft", job_id, job.status)
        return

    pipeline = build_pipeline_chain(job_id)
    result = pipeline.apply_async()

    job.status = "queued"
    job.celery_chain_id = result.id
    job.save(update_fields=["status", "celery_chain_id"])

    logger.info("[start_job] Job %s in Queue eingereiht — Chain-ID: %s", job_id, result.id)
    return result.id
