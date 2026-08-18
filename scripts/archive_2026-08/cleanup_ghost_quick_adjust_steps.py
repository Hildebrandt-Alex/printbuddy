"""
Löscht Ghost Quick Adjust Steps (Status='done', aber kein File auf NAS).

PROBLEM:
- Alte Quick Adjust Steps aus der Zeit vor dem created_at Fix
- Status='done', output_asset_id gesetzt
- ABER: Kein File auf NAS (adjust_colors failed in _save_step)
- Zeigen "Datei nicht gefunden" auf job_results Page

LÖSUNG:
- Finde alle quick_adjust Steps mit output_asset_id
- Prüfe ob Raw-File existiert
- Wenn nicht: Lösche den Step
"""

import os
import sys
import django
import glob
from pathlib import Path

# Django Setup
sys.path.insert(0, '/opt/printbuddy')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'printbuddy.settings.production')
django.setup()

from jobs.models import JobStep

def main():
    raw_dir = Path('/mnt/agency_nas/raw')
    
    # Finde alle Quick Adjust Steps mit Asset
    qa_steps = JobStep.objects.filter(
        step_type='quick_adjust',
        status='done',
        output_asset_id__isnull=False
    ).select_related('job')
    
    print("=== Ghost Quick Adjust Step Cleanup ===")
    print(f"Zu prüfen: {qa_steps.count()} Quick Adjust Steps")
    print()
    
    ghosts = []
    valid = []
    
    for step in qa_steps:
        asset_id = str(step.output_asset_id)
        job_title = step.job.title if step.job else 'Unknown'
        
        # Suche nach adjusted-File (mit Timestamp)
        raw_pattern = str(raw_dir / f"{asset_id}_adjusted_*.png")
        raw_files = glob.glob(raw_pattern)
        
        if not raw_files:
            ghosts.append((step, asset_id, job_title))
        else:
            valid.append((step, asset_id, job_title))
    
    print(f"✅ Valid Steps (mit File): {len(valid)}")
    print(f"👻 Ghost Steps (ohne File): {len(ghosts)}")
    print()
    
    if ghosts:
        print("=== Ghost Steps zum Löschen ===")
        for step, asset_id, job_title in ghosts:
            print(f"  [{job_title}] {asset_id[:12]}... (Step {str(step.id)[:8]})")
        
        print()
        print("=== Lösche Ghost Steps ===")
        for step, asset_id, job_title in ghosts:
            step.delete()
            print(f"  ✅ Gelöscht: [{job_title}] {asset_id[:12]}...")
        
        print()
        print(f"=== {len(ghosts)} Ghost Steps gelöscht ===")
    else:
        print("✅ Keine Ghost Steps gefunden!")

if __name__ == '__main__':
    main()
