import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=10, queue="cpu_queue")
def notify_studio(self, job_id: str):
    """
    Letzter Task in der Pipeline-Chain.
    Setzt Job.status = 'done' und completed_at.
    Studio-Worker sieht das Update über HTMX-Polling (alle 3s).
    """
    logger.info("[notify_studio] Job %s Pipeline abgeschlossen", job_id)

    try:
        from jobs.models import Job, JobStep

        job = Job.objects.get(id=job_id)

        # Prüfen ob alle Steps erfolgreich
        failed_steps = JobStep.objects.filter(job_id=job_id, status="failed")
        if failed_steps.exists():
            failed_names = list(failed_steps.values_list("step_type", flat=True))
            logger.warning("[notify_studio] Job %s hat fehlgeschlagene Steps: %s",
                           job_id, failed_names)
            job.status = "failed"
        else:
            job.status = "done"

        job.completed_at = timezone.now()
        job.save(update_fields=["status", "completed_at"])

        # notify_studio Step als done markieren
        try:
            step = JobStep.objects.get(job_id=job_id, step_type="notify_studio")
            step.status = "done"
            step.started_at = timezone.now()
            step.completed_at = timezone.now()
            step.save(update_fields=["status", "started_at", "completed_at"])
        except JobStep.DoesNotExist:
            pass

        logger.info("[notify_studio] Job %s → status=%s", job_id, job.status)

    except Exception as exc:
        logger.error("[notify_studio] Job %s: %s", job_id, exc)
        raise self.retry(exc=exc)
