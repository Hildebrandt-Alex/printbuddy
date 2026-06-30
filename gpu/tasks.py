import logging
import os
import uuid
from pathlib import Path

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def _get_output_dir(subdir: str) -> Path:
    """Gibt absoluten Pfad zum NAS-Ausgabeverzeichnis zurück."""
    base = Path(getattr(settings, "NAS_BASE_PATH", "/mnt/agency_nas"))
    path = base / subdir
    path.mkdir(parents=True, exist_ok=True)
    return path


def _save_step(job_id: str, step_type: str, status: str, asset_id=None, error_msg=""):
    """JobStep-Status aktualisieren."""
    from jobs.models import JobStep

    try:
        step = JobStep.objects.get(job_id=job_id, step_type=step_type)
        step.status = status
        if status == "running":
            step.started_at = timezone.now()
        elif status in ("done", "failed", "skipped"):
            step.completed_at = timezone.now()
        if asset_id:
            step.output_asset_id = asset_id
        if error_msg:
            step.error_msg = error_msg
        step.save(update_fields=[
            "status", "started_at", "completed_at", "output_asset_id", "error_msg"
        ])
    except JobStep.DoesNotExist:
        logger.warning("JobStep %s/%s nicht gefunden", job_id, step_type)


def _update_job_status(job_id: str, status: str):
    from jobs.models import Job

    fields = ["status"]
    job = Job.objects.get(id=job_id)
    job.status = status
    if status == "running" and not job.started_at:
        job.started_at = timezone.now()
        fields.append("started_at")
    elif status in ("done", "failed"):
        job.completed_at = timezone.now()
        fields.append("completed_at")
    job.save(update_fields=fields)


# ─────────────────────────────────────────────────────────────────────────────
# MOCK: Placeholder-PNG für lokale Tests (MOCK_GPU=true)
# ─────────────────────────────────────────────────────────────────────────────

def _generate_mock_image(job_id: str, width: int, height: int) -> Path:
    """Erzeugt ein farbiges Placeholder-PNG ohne RunPod-Call."""
    from PIL import Image, ImageDraw, ImageFont

    output_dir = _get_output_dir("raw")
    asset_id = uuid.uuid4()
    output_path = output_dir / f"{asset_id}.png"

    img = Image.new("RGB", (width, height), color=(30, 30, 50))
    draw = ImageDraw.Draw(img)
    draw.rectangle([20, 20, width - 20, height - 20], outline=(100, 80, 200), width=4)
    draw.text(
        (width // 2 - 160, height // 2 - 30),
        f"MOCK GPU OUTPUT\nJob: {str(job_id)[:8]}",
        fill=(180, 160, 255),
    )
    img.save(output_path, "PNG")
    logger.info("[MOCK] Placeholder-PNG erzeugt: %s", output_path)
    return output_path, asset_id


# ─────────────────────────────────────────────────────────────────────────────
# TASK: generate_image
# ─────────────────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=30, queue="gpu_queue")
def generate_image(self, job_id: str):
    """
    Generiert ein Bild via RunPod (primary) oder Vast.ai (fallback).
    Bei MOCK_GPU=true wird ein Placeholder-PNG erzeugt.
    """
    from jobs.models import Job

    logger.info("[generate_image] Job %s gestartet", job_id)
    _save_step(job_id, "generate", "running")
    _update_job_status(job_id, "running")

    try:
        job = Job.objects.select_related("pipeline_template").get(id=job_id)
        t = job.pipeline_template

        width = job.width or t.default_width
        height = job.height or t.default_height
        steps = job.num_steps or t.default_steps
        guidance = job.guidance or t.default_guidance
        model = job.model or t.default_model
        prompt = job.prompt
        negative_prompt = job.negative_prompt or ""
        seed = job.seed
        num_images = job.num_images or 1

        # ── MOCK-Modus ───────────────────────────────────────────────────────
        if getattr(settings, "MOCK_GPU", False):
            output_path, asset_id = _generate_mock_image(job_id, width, height)
            _save_step(job_id, "generate", "done", asset_id=asset_id)
            logger.info("[MOCK] generate_image fertig: %s", asset_id)
            return str(asset_id)

        # ── RunPod REST API (primary) ────────────────────────────────────────
        # Für die Public API muss die HTTP REST API direkt aufgerufen werden.
        # runpod.run_sync() funktioniert nur für eigene Serverless-Endpoints.
        try:
            import requests as req
            import time
            import base64

            api_key     = settings.RUNPOD_API_KEY
            endpoint_id = settings.RUNPOD_ENDPOINT_ID
            base_url    = f"https://api.runpod.ai/v2/{endpoint_id}"
            headers     = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            input_payload = {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "width": width,
                "height": height,
                "num_inference_steps": steps,
                "guidance": float(guidance),
                "image_format": "png",
                "seed": seed if seed else -1,
            }

            # Job starten (async)
            logger.info("[RunPod] POST %s/run", base_url)
            run_resp = req.post(
                f"{base_url}/run",
                json={"input": input_payload},
                headers=headers,
                timeout=30,
            )
            run_resp.raise_for_status()
            run_data = run_resp.json()
            run_id   = run_data.get("id")
            if not run_id:
                raise ValueError(f"RunPod: keine Job-ID in Antwort: {run_data}")

            logger.info("[RunPod] Job gestartet: %s", run_id)

            # Auf Ergebnis warten (Polling, max 300s)
            deadline = time.time() + 300
            result   = None
            while time.time() < deadline:
                status_resp = req.get(
                    f"{base_url}/status/{run_id}",
                    headers=headers,
                    timeout=30,
                )
                status_resp.raise_for_status()
                status_data = status_resp.json()
                job_status  = status_data.get("status", "")

                if job_status == "COMPLETED":
                    result = status_data.get("output")
                    break
                elif job_status in ("FAILED", "CANCELLED", "TIMED_OUT"):
                    raise ValueError(f"RunPod Job {run_id} Status: {job_status} — {status_data.get('error', '')}")
                elif job_status in ("IN_QUEUE", "IN_PROGRESS"):
                    logger.debug("[RunPod] Status: %s — warte 3s", job_status)
                    time.sleep(3)
                else:
                    time.sleep(3)

            if result is None:
                raise ValueError(f"RunPod Timeout nach 300s (Job {run_id})")

            # Bild dekodieren + speichern
            output_dir = _get_output_dir("raw")
            asset_id   = uuid.uuid4()
            output_path = output_dir / f"{asset_id}.png"

            # Public API liefert Base64 in result["images"][0] oder result["image"]
            if isinstance(result, list):
                out = result[0]
            else:
                out = result

            if isinstance(out, dict) and out.get("image"):
                image_data = out["image"]
                if "," in image_data:
                    image_data = image_data.split(",", 1)[1]
                output_path.write_bytes(base64.b64decode(image_data))
            elif isinstance(out, dict) and (out.get("image_url") or out.get("url")):
                image_url = out.get("image_url") or out.get("url")
                img_resp  = req.get(image_url, timeout=60)
                img_resp.raise_for_status()
                output_path.write_bytes(img_resp.content)
            elif isinstance(out, str):
                output_path.write_bytes(base64.b64decode(out))
            elif isinstance(result, dict) and result.get("images"):
                # Manche Modelle liefern {"images": ["base64..."]}
                image_data = result["images"][0]
                if "," in image_data:
                    image_data = image_data.split(",", 1)[1]
                output_path.write_bytes(base64.b64decode(image_data))
            else:
                raise ValueError(f"Unbekanntes RunPod Output-Format: {type(out)}: {str(out)[:300]}")

            logger.info("[RunPod] Bild gespeichert: %s", output_path)
            _save_step(job_id, "generate", "done", asset_id=asset_id)
            return str(asset_id)

        except Exception as runpod_exc:
            logger.error("[RunPod] Fehler: %s", runpod_exc)
            # Kein Vast.ai Fallback — direkt als failed melden mit klarer Fehlermeldung
            raise runpod_exc

    except Exception as exc:
        logger.error("[generate_image] Job %s fehlgeschlagen: %s", job_id, exc)
        _save_step(job_id, "generate", "failed", error_msg=str(exc))
        _update_job_status(job_id, "failed")
        raise self.retry(exc=exc)


# ─────────────────────────────────────────────────────────────────────────────
# TASK: upscale_image
# ─────────────────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=30, queue="gpu_queue")
def upscale_image(self, job_id: str):
    """
    4x Real-ESRGAN Upscaling via RunPod.
    Bei MOCK_GPU=true wird das Raw-Bild einfach kopiert (kein echter Upscale).
    """
    from jobs.models import Job, JobStep

    logger.info("[upscale_image] Job %s gestartet", job_id)
    _save_step(job_id, "upscale", "running")

    try:
        job = Job.objects.get(id=job_id)

        # Asset-ID vom generate-Step holen
        try:
            gen_step = JobStep.objects.get(job_id=job_id, step_type="generate", status="done")
            source_asset_id = str(gen_step.output_asset_id)
        except JobStep.DoesNotExist:
            raise ValueError("generate-Step nicht done — kann nicht upscalen")

        raw_dir = _get_output_dir("raw")
        source_path = raw_dir / f"{source_asset_id}.png"

        if not source_path.exists():
            raise FileNotFoundError(f"Quell-Bild nicht gefunden: {source_path}")

        # ── MOCK-Modus ───────────────────────────────────────────────────────
        if getattr(settings, "MOCK_GPU", False):
            import shutil
            asset_id = uuid.uuid4()
            output_path = raw_dir / f"{asset_id}_4x.png"
            shutil.copy2(source_path, output_path)
            _save_step(job_id, "upscale", "done", asset_id=asset_id)
            logger.info("[MOCK] upscale_image fertig: %s", asset_id)
            return str(asset_id)

        # ── RunPod Real-ESRGAN ───────────────────────────────────────────────
        import base64
        import requests
        import runpod

        runpod.api_key = settings.RUNPOD_API_KEY

        with open(source_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode()

        result = runpod.run_sync(
            endpoint_id=settings.RUNPOD_UPSCALE_ENDPOINT,
            input={"image": image_b64, "scale": 4},
            timeout=180,
        )

        if not result or "output" not in result:
            raise ValueError(f"RunPod Upscale leere Antwort: {result}")

        upscaled_b64 = result["output"].get("image")
        if not upscaled_b64:
            raise ValueError("Kein Bild im Upscale-Output")

        asset_id = uuid.uuid4()
        output_path = raw_dir / f"{asset_id}_4x.png"
        output_path.write_bytes(base64.b64decode(upscaled_b64))

        logger.info("[RunPod] Upscale fertig: %s", output_path)
        _save_step(job_id, "upscale", "done", asset_id=asset_id)
        return str(asset_id)

    except Exception as exc:
        logger.error("[upscale_image] Job %s fehlgeschlagen: %s", job_id, exc)
        _save_step(job_id, "upscale", "failed", error_msg=str(exc))
        raise self.retry(exc=exc)
