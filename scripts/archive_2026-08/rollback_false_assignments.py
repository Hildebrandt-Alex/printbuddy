from jobs.models import Job, JobStep
from django.utils import timezone

print("=== Rollback falscher Quick Adjust Zuweisungen ===\n")

# Asset-IDs die mehrfach zugewiesen wurden (FALSCH)
problematic_assets = [
    'af93325d-3d9d-4d5c-9e9c-e00c6e97b05b',  # 4 Jobs
    '843ff5c4-47f7-4d31-9055-1dadbd5adf4b',  # 3 Jobs  
    '8b3f4086-0226-4ae8-8021-48dec79cbe57',  # 2 Jobs
    'bf0c505f-f7a8-4cfe-8ff3-f9ea5058fbc3',  # 2 Jobs (aber Original von sdxl)
]

# Für jeden problematic Asset: Behalte nur den ÄLTESTEN Step (vermutlich der echte)
rollback_count = 0
kept_count = 0

for asset_id in problematic_assets:
    steps = JobStep.objects.filter(
        output_asset_id=asset_id,
        step_type='quick_adjust'
    ).select_related('job').order_by('completed_at')
    
    if steps.count() <= 1:
        print(f"Asset {asset_id[:8]}: Nur 1 Step, kein Rollback nötig")
        continue
    
    print(f"\nAsset {asset_id[:8]}: {steps.count()} Steps gefunden")
    
    # Ältester Step = vermutlich der echte
    original_step = steps.first()
    print(f"  ✅ BEHALTEN: Job {original_step.job.title} ({str(original_step.job.id)[:8]})")
    print(f"     Completed: {original_step.completed_at}")
    kept_count += 1
    
    # Alle anderen Steps: Zurücksetzen
    for step in steps[1:]:
        print(f"  ❌ ROLLBACK: Job {step.job.title} ({str(step.job.id)[:8]})")
        print(f"     Completed: {step.completed_at}")
        
        # Reset auf Zustand vor Repair
        step.output_asset_id = None
        step.status = 'pending'
        step.started_at = None
        step.completed_at = None
        step.save(update_fields=['output_asset_id', 'status', 'started_at', 'completed_at'])
        rollback_count += 1

print(f"\n{'='*60}")
print(f"✅ Steps behalten: {kept_count}")
print(f"❌ Steps zurückgesetzt: {rollback_count}")

# Zeige finale Job-Übersicht
print(f"\n{'='*60}")
print("=== Quick Adjust Status nach Rollback ===\n")

jobs = Job.objects.filter(title__in=['test22', 'sdxl', 'maxtest2']).order_by('title')

for job in jobs:
    qa_steps = job.steps.filter(step_type='quick_adjust').order_by('order')
    qa_with_assets = qa_steps.filter(output_asset_id__isnull=False).count()
    qa_pending = qa_steps.filter(status='pending').count()
    
    print(f"Job: {job.title} ({str(job.id)[:8]})")
    print(f"  Quick Adjust Steps: {qa_steps.count()} total")
    print(f"  Mit Assets: {qa_with_assets}")
    print(f"  Pending: {qa_pending}\n")
