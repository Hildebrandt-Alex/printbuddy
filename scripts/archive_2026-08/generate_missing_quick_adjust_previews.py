"""
Generiert fehlende Preview-Dateien für alle Quick Adjust Assets.

PROBLEM:
- Quick Adjust Assets wurden erstellt (raw/*.png)
- ABER: Previews (exports/preview/*.jpg) fehlen
- Grund: _get_latest_asset fand das falsche Asset

LÖSUNG:
- Finde alle quick_adjust Steps mit output_asset_id
- Prüfe ob Preview existiert
- Wenn nicht: Generiere Preview manuell (JPG 72dpi max 1200px)
"""

import os
import sys
import django
import glob
from pathlib import Path
from PIL import Image

# Django Setup
sys.path.insert(0, '/opt/printbuddy')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'printbuddy.settings.production')
django.setup()

from jobs.models import JobStep

def generate_preview_for_asset(asset_id: str, raw_file: Path, preview_dir: Path):
    """Generiert Preview-JPG für ein adjusted Asset"""
    preview_path = preview_dir / f"{asset_id}.jpg"
    
    # Skip wenn Preview bereits existiert
    if preview_path.exists():
        print(f"  ✓ Preview existiert bereits: {preview_path.name}")
        return False
    
    try:
        with Image.open(raw_file) as img:
            if img.mode != "RGB":
                img = img.convert("RGB")
            
            # Auf max 1200px skalieren (gleiche Logik wie preview_export Task)
            img.thumbnail((1200, 1200), Image.LANCZOS)
            img.save(preview_path, "JPEG", quality=88, dpi=(72, 72))
            
            # NFS-Permissions fix für Nginx-Zugriff
            os.chmod(preview_path, 0o666)
        
        print(f"  ✅ Preview erstellt: {preview_path.name}")
        return True
    
    except Exception as e:
        print(f"  ❌ Fehler beim Generieren: {e}")
        return False

def main():
    raw_dir = Path('/mnt/agency_nas/raw')
    preview_dir = Path('/mnt/agency_nas/exports/preview')
    
    # Finde alle Quick Adjust Steps mit Asset
    qa_steps = JobStep.objects.filter(
        step_type='quick_adjust',
        status='done',
        output_asset_id__isnull=False
    ).select_related('job')
    
    print(f"=== Quick Adjust Preview Generator ===")
    print(f"Gefunden: {qa_steps.count()} Quick Adjust Steps")
    print()
    
    generated = 0
    skipped = 0
    errors = 0
    
    for step in qa_steps:
        asset_id = str(step.output_asset_id)
        job_title = step.job.title if step.job else 'Unknown'
        
        print(f"[{job_title}] Asset {asset_id[:12]}...")
        
        # Suche nach adjusted-File (mit Timestamp)
        raw_pattern = raw_dir / f"{asset_id}_adjusted_*.png"
        raw_files = sorted(
            glob.glob(str(raw_pattern)),
            key=lambda p: Path(p).stat().st_mtime,
            reverse=True
        )
        
        if not raw_files:
            print(f"  ⚠️  Raw-File nicht gefunden: {raw_pattern.name}")
            errors += 1
            continue
        
        raw_file = Path(raw_files[0])
        print(f"  Raw File: {raw_file.name}")
        
        # Preview generieren
        if generate_preview_for_asset(asset_id, raw_file, preview_dir):
            generated += 1
        else:
            skipped += 1
        
        print()
    
    print("=== Zusammenfassung ===")
    print(f"✅ Generiert: {generated}")
    print(f"⏭️  Übersprungen (existierten): {skipped}")
    print(f"❌ Fehler: {errors}")
    print()
    print("=== Abgeschlossen ===")

if __name__ == '__main__':
    main()
