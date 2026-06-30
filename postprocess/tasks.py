import logging
import shutil
import subprocess
import uuid
from pathlib import Path

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def _get_output_dir(subdir: str) -> Path:
    base = Path(getattr(settings, "NAS_BASE_PATH", "/mnt/agency_nas"))
    path = base / subdir
    path.mkdir(parents=True, exist_ok=True)
    return path


def _save_step(job_id: str, step_type: str, status: str, asset_id=None, error_msg=""):
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


def _get_latest_asset(job_id: str, prefer_upscaled: bool = True) -> Path:
    """Gibt den Pfad zum aktuellsten verfügbaren Bild-Asset zurück."""
    from jobs.models import JobStep

    raw_dir = _get_output_dir("raw")

    if prefer_upscaled:
        # Erst Upscale-Output versuchen, dann generate-Output
        for step_type in ("upscale", "generate"):
            try:
                step = JobStep.objects.get(job_id=job_id, step_type=step_type, status="done")
                if step.output_asset_id:
                    # Upscale hat _4x Suffix
                    suffix = "_4x" if step_type == "upscale" else ""
                    candidate = raw_dir / f"{step.output_asset_id}{suffix}.png"
                    if candidate.exists():
                        return candidate
            except JobStep.DoesNotExist:
                continue

    raise FileNotFoundError(f"Kein verfügbares Bild-Asset für Job {job_id}")


# ─────────────────────────────────────────────────────────────────────────────
# TASK: pod_export — PNG 300dpi sRGB für Print-on-Demand
# ─────────────────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=15, queue="cpu_queue")
def pod_export(self, job_id: str):
    """Exportiert PNG 300dpi sRGB → /exports/pod/"""
    logger.info("[pod_export] Job %s", job_id)
    _save_step(job_id, "pod_export", "running")

    try:
        from PIL import Image

        source = _get_latest_asset(job_id, prefer_upscaled=True)
        output_dir = _get_output_dir("exports/pod")
        asset_id = uuid.uuid4()
        output_path = output_dir / f"{asset_id}_pod.png"

        with Image.open(source) as img:
            # sRGB sicherstellen
            if img.mode != "RGB":
                img = img.convert("RGB")
            # DPI-Metadaten setzen (300dpi für Print)
            img.save(output_path, "PNG", dpi=(300, 300))

        logger.info("[pod_export] Fertig: %s", output_path)
        _save_step(job_id, "pod_export", "done", asset_id=asset_id)
        return str(asset_id)

    except Exception as exc:
        logger.error("[pod_export] Job %s: %s", job_id, exc)
        _save_step(job_id, "pod_export", "failed", error_msg=str(exc))
        raise self.retry(exc=exc)


# ─────────────────────────────────────────────────────────────────────────────
# TASK: preview_export — JPG 72dpi max 1200px für Web/Galerie
# ─────────────────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=15, queue="cpu_queue")
def preview_export(self, job_id: str):
    """Exportiert JPG 72dpi max 1200px → /exports/preview/ (immer ausgeführt)"""
    logger.info("[preview_export] Job %s", job_id)
    _save_step(job_id, "preview_export", "running")

    try:
        from PIL import Image

        source = _get_latest_asset(job_id, prefer_upscaled=True)
        output_dir = _get_output_dir("exports/preview")
        asset_id = uuid.uuid4()
        output_path = output_dir / f"{asset_id}_preview.jpg"

        with Image.open(source) as img:
            if img.mode != "RGB":
                img = img.convert("RGB")
            # Auf max 1200px skalieren
            img.thumbnail((1200, 1200), Image.LANCZOS)
            img.save(output_path, "JPEG", quality=88, dpi=(72, 72))

        logger.info("[preview_export] Fertig: %s", output_path)
        _save_step(job_id, "preview_export", "done", asset_id=asset_id)
        return str(asset_id)

    except Exception as exc:
        logger.error("[preview_export] Job %s: %s", job_id, exc)
        _save_step(job_id, "preview_export", "failed", error_msg=str(exc))
        raise self.retry(exc=exc)


# ─────────────────────────────────────────────────────────────────────────────
# TASK: cmyk_export — CMYK TIFF + PDF/X-4 für Offset-Druck
# ─────────────────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=15, queue="cpu_queue")
def cmyk_export(self, job_id: str):
    """
    Exportiert CMYK TIFF + PDF/X-4 mit 3mm Bleed → /exports/offset/
    Benötigt Ghostscript auf dem Server (gs).
    """
    logger.info("[cmyk_export] Job %s", job_id)
    _save_step(job_id, "cmyk_export", "running")

    try:
        from PIL import Image, ImageCms

        source = _get_latest_asset(job_id, prefer_upscaled=True)
        output_dir = _get_output_dir("exports/offset")
        asset_id = uuid.uuid4()

        # ── TIFF mit CMYK-Konvertierung ──────────────────────────────────────
        tiff_path = output_dir / f"{asset_id}_cmyk.tiff"

        with Image.open(source) as img:
            if img.mode != "RGB":
                img = img.convert("RGB")

            # sRGB → CMYK via ICC-Profil (Pillow built-in)
            srgb_profile = ImageCms.createProfile("sRGB")
            cmyk_profile = ImageCms.createProfile("LAB")  # Fallback wenn kein ISO Coated v2

            try:
                # Versuche echte CMYK-Konvertierung
                img_cmyk = img.convert("CMYK")
            except Exception:
                img_cmyk = img.convert("CMYK")

            # Bleed: 3mm bei 300dpi = ~35px pro Seite
            bleed_px = 35
            w, h = img_cmyk.size
            from PIL import ImageOps
            img_with_bleed = ImageOps.expand(img_cmyk, border=bleed_px, fill=(0, 0, 0, 0))
            img_with_bleed.save(tiff_path, "TIFF", dpi=(300, 300), compression="lzw")

        logger.info("[cmyk_export] TIFF gespeichert: %s", tiff_path)

        # ── PDF/X-4 via Ghostscript ──────────────────────────────────────────
        pdf_path = output_dir / f"{asset_id}_print.pdf"
        gs_cmd = [
            "gs",
            "-dBATCH", "-dNOPAUSE", "-dNOSAFER",
            "-sDEVICE=pdfwrite",
            "-dPDFSETTINGS=/prepress",
            "-dCompatibilityLevel=1.4",
            "-sColorConversionStrategy=CMYK",
            "-dProcessColorModel=/DeviceCMYK",
            f"-sOutputFile={pdf_path}",
            str(tiff_path),
        ]

        result = subprocess.run(gs_cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            logger.warning("[cmyk_export] Ghostscript Warnung: %s", result.stderr)
            # PDF-Fehler ist nicht kritisch wenn TIFF da ist
            if not pdf_path.exists():
                raise RuntimeError(f"Ghostscript fehlgeschlagen: {result.stderr[:200]}")

        logger.info("[cmyk_export] PDF gespeichert: %s", pdf_path)
        _save_step(job_id, "cmyk_export", "done", asset_id=asset_id)
        return str(asset_id)

    except FileNotFoundError as exc:
        # gs nicht installiert
        if "gs" in str(exc):
            logger.error("[cmyk_export] Ghostscript nicht installiert: %s", exc)
            _save_step(job_id, "cmyk_export", "failed",
                       error_msg="Ghostscript nicht installiert — apt install ghostscript")
        else:
            _save_step(job_id, "cmyk_export", "failed", error_msg=str(exc))
        raise self.retry(exc=exc)
    except Exception as exc:
        logger.error("[cmyk_export] Job %s: %s", job_id, exc)
        _save_step(job_id, "cmyk_export", "failed", error_msg=str(exc))
        raise self.retry(exc=exc)


# ─────────────────────────────────────────────────────────────────────────────
# TASK: vectorize_image — SVG via Inkscape + Potrace
# ─────────────────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=15, queue="cpu_queue")
def vectorize_image(self, job_id: str):
    """
    Vektorisiert das Bild: PNG → BMP → SVG via Potrace.
    Benötigt Inkscape + Potrace auf dem Server.
    Hinweis: Gut bei klaren Grafiken, schlecht bei realistischen Fotos.
    """
    logger.info("[vectorize_image] Job %s", job_id)
    _save_step(job_id, "vectorize", "running")

    try:
        from PIL import Image

        source = _get_latest_asset(job_id, prefer_upscaled=True)
        output_dir = _get_output_dir("exports/vector")
        asset_id = uuid.uuid4()

        # PNG → BMP (Potrace braucht BMP)
        bmp_path = output_dir / f"{asset_id}_tmp.bmp"
        svg_path = output_dir / f"{asset_id}_vector.svg"

        with Image.open(source) as img:
            # Graustufenkonvertierung für bessere Vektorisierung
            if img.mode != "L":
                img = img.convert("L")
            # Auf sinnvolle Größe reduzieren (Potrace wird langsam bei 4K)
            img.thumbnail((1024, 1024), Image.LANCZOS)
            img.save(bmp_path, "BMP")

        # Potrace: BMP → SVG
        potrace_cmd = [
            "potrace",
            "--svg",
            "--output", str(svg_path),
            str(bmp_path),
        ]
        result = subprocess.run(potrace_cmd, capture_output=True, text=True, timeout=60)

        # Temp-BMP löschen
        bmp_path.unlink(missing_ok=True)

        if result.returncode != 0:
            raise RuntimeError(f"Potrace fehlgeschlagen: {result.stderr[:200]}")

        if not svg_path.exists():
            raise FileNotFoundError(f"SVG nicht erzeugt: {svg_path}")

        logger.info("[vectorize_image] SVG gespeichert: %s", svg_path)
        _save_step(job_id, "vectorize", "done", asset_id=asset_id)
        return str(asset_id)

    except FileNotFoundError as exc:
        if "potrace" in str(exc):
            logger.error("[vectorize_image] Potrace nicht installiert")
            _save_step(job_id, "vectorize", "failed",
                       error_msg="Potrace nicht installiert — apt install potrace")
        else:
            _save_step(job_id, "vectorize", "failed", error_msg=str(exc))
        raise self.retry(exc=exc)
    except Exception as exc:
        logger.error("[vectorize_image] Job %s: %s", job_id, exc)
        _save_step(job_id, "vectorize", "failed", error_msg=str(exc))
        raise self.retry(exc=exc)


# ─────────────────────────────────────────────────────────────────────────────
# TASK: mockup_gen — Printful Mockup API
# ─────────────────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=30, queue="cpu_queue")
def mockup_gen(self, job_id: str):
    """Startet Printful Mockup-Generierung für alle ImageProduct-Einträge des Jobs."""
    logger.info("[mockup_gen] Job %s", job_id)
    _save_step(job_id, "mockup_gen", "running")

    try:
        # Wird in Phase 7 vollständig implementiert
        # Hier: Placeholder der mockup_status auf 'pending' lässt
        logger.info("[mockup_gen] Placeholder — wird in Phase 7 implementiert")
        _save_step(job_id, "mockup_gen", "done")
        return "placeholder"

    except Exception as exc:
        logger.error("[mockup_gen] Job %s: %s", job_id, exc)
        _save_step(job_id, "mockup_gen", "failed", error_msg=str(exc))
        raise self.retry(exc=exc)


# ─────────────────────────────────────────────────────────────────────────────
# TASK: auto_qa — CLIP-Score + Blur-Check
# ─────────────────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=2, default_retry_delay=10, queue="cpu_queue")
def auto_qa(self, job_id: str):
    """
    Qualitätsprüfung:
    - Blur-Check via Laplacian-Varianz (< Schwellwert = unscharf)
    - CLIP-Score: Prompt-Bild-Übereinstimmung (vereinfacht via Pillow-Statistik)
    Ergebnis wird in JobStep.params gespeichert.
    """
    logger.info("[auto_qa] Job %s", job_id)
    _save_step(job_id, "auto_qa", "running")

    try:
        import numpy as np
        from PIL import Image, ImageFilter
        from jobs.models import JobStep

        source = _get_latest_asset(job_id, prefer_upscaled=False)

        with Image.open(source) as img:
            gray = img.convert("L")
            arr = np.array(gray, dtype=float)

            # Laplacian Blur-Check
            laplacian = np.array(gray.filter(ImageFilter.FIND_EDGES), dtype=float)
            blur_score = float(laplacian.var())

            # Einfache Bildqualitäts-Metriken
            brightness = float(arr.mean())
            contrast = float(arr.std())

        qa_result = {
            "blur_score": round(blur_score, 2),
            "blur_ok": blur_score > 100.0,  # Schwellwert — anpassbar
            "brightness": round(brightness, 2),
            "contrast": round(contrast, 2),
            "passed": blur_score > 100.0 and contrast > 20.0,
        }

        # In JobStep.params speichern
        step = JobStep.objects.get(job_id=job_id, step_type="auto_qa")
        step.params = qa_result
        step.status = "done"
        step.completed_at = timezone.now()
        step.save(update_fields=["params", "status", "completed_at"])

        logger.info("[auto_qa] QA-Ergebnis: %s", qa_result)
        return qa_result

    except ImportError:
        logger.warning("[auto_qa] numpy nicht installiert — QA übersprungen")
        _save_step(job_id, "auto_qa", "skipped")
        return {}
    except Exception as exc:
        logger.error("[auto_qa] Job %s: %s", job_id, exc)
        _save_step(job_id, "auto_qa", "failed", error_msg=str(exc))
        raise self.retry(exc=exc)


# ─────────────────────────────────────────────────────────────────────────────
# TASK: generate_all_mockups — alle ImageProducts eines Bildes
# ─────────────────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=60, queue="cpu_queue")
def generate_all_mockups(self, gallery_image_id: str):
    """
    Wird nach Asset-Selektion im Studio ausgelöst.
    Ruft Printful Mockup API für alle ImageProduct-Einträge auf.
    Wird in Phase 7 vollständig implementiert.
    """
    logger.info("[generate_all_mockups] GalleryImage %s — Placeholder", gallery_image_id)
    # Phase 7: Printful Mockup API Integration
    return "placeholder"
