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

        # ── Modell-spezifischen Endpoint wählen ──────────────────────────────
        is_sdxl     = (model == "sdxl")
        is_img2img  = bool(job.reference_image)

        if is_sdxl:
            endpoint_id = getattr(settings, "RUNPOD_SDXL_ENDPOINT_ID", "")
            if not endpoint_id:
                raise ValueError(
                    "SDXL Job benötigt RUNPOD_SDXL_ENDPOINT_ID in .env!\n"
                    "Bitte setzen: RUNPOD_SDXL_ENDPOINT_ID=vdjnfxf6h8q0ra"
                )
            logger.info(f"[SDXL] Verwende Endpoint: {endpoint_id}")
        else:
            endpoint_id = getattr(settings, "RUNPOD_ENDPOINT_ID", "")
            if not endpoint_id:
                raise ValueError(
                    "FLUX Job benötigt RUNPOD_ENDPOINT_ID in .env!\n"
                    "Bitte setzen: RUNPOD_ENDPOINT_ID=black-forest-labs-flux-1-schnell"
                )
            logger.info(f"[FLUX] Verwende Endpoint: {endpoint_id}")

        logger.info(f"Job {job_id}: model={model}, is_sdxl={is_sdxl}, is_img2img={is_img2img}, endpoint={endpoint_id}")

        # ── RunPod REST API (primary) ────────────────────────────────────────
        try:
            import requests as req
            import time
            import base64

            api_key     = settings.RUNPOD_API_KEY
            base_url    = f"https://api.runpod.ai/v2/{endpoint_id}"
            headers     = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            input_payload: dict

            if is_sdxl:
                # SDXL Worker 2.1.1 API-Contract (runpod-workers/worker-sdxl)
                # Endpoint: vdjnfxf6h8q0ra
                # Doku: https://github.com/runpod-workers/worker-sdxl
                
                # SDXL-spezifische Parameter aus Job.notes parsen (falls vom Wizard gesetzt)
                refiner_steps = 50
                scheduler = "K_EULER"
                high_noise_frac = 0.8
                
                if job.notes:
                    import re
                    # Format: "SDXL: Refiner=50 Scheduler=K_EULER HighNoise=0.8"
                    refiner_match = re.search(r'Refiner=(\d+)', job.notes)
                    scheduler_match = re.search(r'Scheduler=(\w+)', job.notes)
                    noise_match = re.search(r'HighNoise=([\d.]+)', job.notes)
                    
                    if refiner_match: refiner_steps = int(refiner_match.group(1))
                    if scheduler_match: scheduler = scheduler_match.group(1)
                    if noise_match: high_noise_frac = float(noise_match.group(1))
                
                # SDXL Worker: Auflösung limitieren (Worker-Bug: große Outputs → 400 beim Upload)
                sdxl_width = min(width, 768)
                sdxl_height = min(height, 768)
                if width > 768 or height > 768:
                    logger.warning(f"[SDXL] Auflösung reduziert: {width}x{height} → {sdxl_width}x{sdxl_height}")
                
                # SDXL Worker erwartet "input"-Wrapper mit spezifischen Keys
                input_payload = {
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "width": sdxl_width,
                    "height": sdxl_height,
                    "num_inference_steps": steps,
                    "refiner_inference_steps": refiner_steps,
                    "guidance_scale": float(guidance),
                    "high_noise_frac": high_noise_frac,
                    "scheduler": scheduler,
                    "seed": seed if seed else -1,  # -1 = random für SDXL
                    "num_images": num_images,
                    # ACHTUNG: "refine" gibt "Unexpected input" Error → entfernt
                }
                logger.info(f"[RunPod/SDXL] Payload Keys: {list(input_payload.keys())}")
            else:
                # FLUX Worker API-Contract
                # FLUX Schnell: max. 8 Steps (optimiert für 1-4)
                flux_steps = min(steps, 8)
                if steps > 8:
                    logger.warning(f"FLUX Schnell Steps limitiert: {steps} → 8 (RunPod Constraint)")
                
                input_payload = {
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "width": width,
                    "height": height,
                    "num_inference_steps": flux_steps,
                    "guidance_scale": float(guidance),
                    "image_format": "png",
                    "seed": seed if seed else -1,
                    "num_images": num_images,
                }

            # Img2Img: Stärke + Referenzbild eintragen
            if is_img2img and job.reference_image:
                try:
                    # Strength aus Job-Notes extrahieren
                    img2img_strength = 0.75
                    for line in (job.notes or "").splitlines():
                        if "Img2Img" in line and ":" in line:
                            try:
                                img2img_strength = float(line.split(":")[-1].strip())
                            except ValueError:
                                pass

                    # Referenzbild als Base64 laden (für beide Modelle)
                    from django.core.files.storage import default_storage
                    from PIL import Image
                    import io
                    
                    # Bild laden und ggf. auf max 768x768 resizen (Worker-Performance)
                    with default_storage.open(job.reference_image.name) as f:
                        img = Image.open(f)
                        img = img.convert('RGB')  # SDXL braucht RGB
                        
                        # Resize wenn zu groß (aspect ratio beibehalten)
                        max_size = 768
                        if img.width > max_size or img.height > max_size:
                            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                            logger.info(f"[Img2Img] Resized to {img.width}x{img.height}")
                        
                        # Als PNG in Memory speichern
                        buffer = io.BytesIO()
                        img.save(buffer, format='PNG')
                        img_bytes = buffer.getvalue()
                        ref_b64 = base64.b64encode(img_bytes).decode()
                    
                    if is_sdxl:
                        # SDXL Worker: "image_url" mit data URI (laut offizieller Doku!)
                        input_payload["image_url"] = f"data:image/png;base64,{ref_b64}"
                        input_payload["strength"] = img2img_strength
                        logger.info("[RunPod/SDXL] Img2Img Modus aktiv (image_url data URI), Stärke: %s", img2img_strength)
                    else:
                        # FLUX Worker: base64-Bild übergeben
                        input_payload["image"] = ref_b64
                        input_payload["strength"] = img2img_strength
                        input_payload["mode"] = "img2img"
                        logger.info("[RunPod/FLUX] Img2Img Modus aktiv (base64), Stärke: %s", img2img_strength)
                except Exception as ref_exc:
                    logger.warning("[RunPod] Referenzfoto konnte nicht gelesen werden: %s — fahre als Text2Img fort", ref_exc)

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
            logger.info("[RunPod] Console: https://www.runpod.io/console/serverless/user/jobs")

            # Auf Ergebnis warten (Polling)
            # SDXL + Refiner braucht länger als FLUX
            timeout_seconds = 900 if is_sdxl else 300  # 15min für SDXL, 5min für FLUX
            deadline = time.time() + timeout_seconds
            result   = None
            last_status = None
            elapsed_start = time.time()
            
            while time.time() < deadline:
                elapsed = int(time.time() - elapsed_start)
                status_resp = req.get(
                    f"{base_url}/status/{run_id}",
                    headers=headers,
                    timeout=30,
                )
                status_resp.raise_for_status()
                status_data = status_resp.json()
                job_status  = status_data.get("status", "")
                last_status = job_status

                if job_status == "COMPLETED":
                    result = status_data.get("output")
                    if result is None:
                        # Output kann auch direkt im status_data liegen oder unter anderem Key
                        logger.warning(f"[RunPod] ⚠️ COMPLETED aber 'output' ist None — status_data Keys: {list(status_data.keys())}")
                        logger.warning(f"[RunPod] Full response: {status_data}")
                        # Versuche alternative Keys
                        if "result" in status_data:
                            result = status_data["result"]
                        elif "images" in status_data:
                            result = status_data["images"]
                        else:
                            # Letzter Versuch: gesamtes status_data als result
                            result = status_data
                    else:
                        # SDXL Worker 2.1.1: {"output": {"images": ["data:image/png;base64,..."], "seed": 42}}
                        if isinstance(result, dict):
                            if "images" in result and result["images"]:
                                result = result["images"]  # Liste von Base64-Strings
                                logger.info(f"[RunPod] Output.images[] enthält {len(result)} Bild(er)")
                            elif "image_url" in result:
                                result = [result["image_url"]]
                    logger.info(f"[RunPod] ✅ COMPLETED nach {elapsed}s")
                    break
                elif job_status in ("FAILED", "CANCELLED", "TIMED_OUT"):
                    error_detail = status_data.get("error", status_data)
                    logger.error(f"[RunPod] ❌ {job_status} nach {elapsed}s — Details: {error_detail}")
                    raise ValueError(f"RunPod Job {run_id} Status: {job_status} — {error_detail}")
                elif job_status == "IN_QUEUE":
                    logger.info(f"[RunPod] ⏳ IN_QUEUE ({elapsed}s) — wartet auf freien Worker...")
                    time.sleep(5)  # Länger warten wenn in Queue
                elif job_status == "IN_PROGRESS":
                    logger.info(f"[RunPod] 🔄 IN_PROGRESS ({elapsed}s) — generiert Bild...")
                    time.sleep(3)
                else:
                    logger.warning(f"[RunPod] ❓ Unbekannter Status: {job_status} ({elapsed}s)")
                    time.sleep(3)

            if result is None:
                logger.error(f"[RunPod] ⏱️ Result ist None — Letzter Status: {last_status}")
                logger.error(f"[RunPod] COMPLETED Response Keys: {list(status_data.keys())}")
                logger.error(f"[RunPod] COMPLETED Full Response: {status_data}")
                
                # Letzter Versuch: Job direkt von RunPod abrufen (manchmal ist Output verzögert)
                logger.info("[RunPod] Versuche direkten Job-Abruf...")
                try:
                    direct_resp = req.get(f"{base_url}/status/{run_id}", headers=headers, timeout=30)
                    direct_data = direct_resp.json()
                    logger.info(f"[RunPod] Direkter Abruf — Keys: {list(direct_data.keys())}")
                    logger.info(f"[RunPod] Direkter Abruf — Full: {direct_data}")
                except Exception as e:
                    logger.error(f"[RunPod] Direkter Abruf fehlgeschlagen: {e}")
                
                raise ValueError(
                    f"RunPod Job {run_id} — Output fehlt komplett!\n"
                    f"Status: {last_status}\n"
                    f"Response hatte nur: {list(status_data.keys())}\n"
                    f"SDXL Worker gibt möglicherweise kein Output zurück.\n"
                    f"Prüfe: https://www.runpod.io/console/serverless/user/jobs/{run_id}"
                )

            # Bild dekodieren + speichern
            logger.info(f"[RunPod] Dekodiere Output — Type: {type(result)}, Keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
            output_dir = _get_output_dir("raw")
            asset_id   = uuid.uuid4()
            output_path = output_dir / f"{asset_id}.png"

            # SDXL Worker 2.1.1 liefert Liste: ["data:image/png;base64,..."]
            if isinstance(result, list):
                out = result[0]
            elif isinstance(result, dict) and "images" in result:
                out = result["images"][0]
            elif isinstance(result, dict) and "image_url" in result:
                out = result["image_url"]
            else:
                out = result

            if isinstance(out, dict) and out.get("image"):
                image_data = out["image"]
                # Strip data URI prefix: "data:image/png;base64,..."
                if "," in image_data:
                    image_data = image_data.split(",", 1)[1]
                output_path.write_bytes(base64.b64decode(image_data))
            elif isinstance(out, dict) and (out.get("image_url") or out.get("url") or out.get("result")):
                image_url = out.get("image_url") or out.get("url") or out.get("result")
                img_resp  = req.get(image_url, timeout=60)
                img_resp.raise_for_status()
                # JPEG von RunPod als PNG-Datei speichern (Pillow konvertiert)
                from PIL import Image as PilImage
                import io
                pil_img = PilImage.open(io.BytesIO(img_resp.content)).convert("RGB")
                output_path = output_path.with_suffix(".png")
                pil_img.save(output_path, "PNG")
            
            elif isinstance(out, str):
                # SDXL Worker: "data:image/png;base64,iVBORw0KG..." -> strip prefix
                image_data = out
                if image_data.startswith("data:"):
                    # Strip "data:image/png;base64," prefix
                    if "," in image_data:
                        image_data = image_data.split(",", 1)[1]
                output_path.write_bytes(base64.b64decode(image_data))
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
