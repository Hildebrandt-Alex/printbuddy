from jobs.models import Job, JobStep

# Asset-IDs aus test22 Quick Adjust Steps
test22_qa_assets = [
    'ba274f35-5dc3-4e9a-8ba5-d5ee351faa16',  # Order 4 (echt)
    'af93325d-3d9d-4d5c-9e9c-e00c6e97b05b',  # Order 5 (repair)
    '843ff5c4-47f7-4d31-9055-1dadbd5adf4b',  # Order 6 (repair)
    '8b3f4086-0226-4ae8-8021-48dec79cbe57',  # Order 7 (repair)
    'bf0c505f-f7a8-4cfe-8ff3-f9ea5058fbc3',  # Order 8 (repair)
]

print("=== Asset Ownership Check ===\n")

for asset_id in test22_qa_assets:
    print(f"\nAsset: {asset_id}")
    
    # Finde ALLE Steps die dieses Asset verwenden
    steps = JobStep.objects.filter(output_asset_id=asset_id).select_related('job')
    
    if not steps:
        print("  ❌ Kein Step gefunden!")
        continue
    
    for step in steps:
        job = step.job
        print(f"  Job: {job.title} ({str(job.id)[:8]})")
        print(f"    Step Type: {step.step_type}")
        print(f"    Step Order: {step.order}")
        print(f"    Completed: {step.completed_at}")
        
print("\n\n=== Original Job Assets ===")
# Für jeden Job: Zeige generate/preview Assets
jobs = Job.objects.filter(title__in=['test22', 'sdxl', 'maxtest2']).order_by('title')

for job in jobs:
    print(f"\nJob: {job.title} ({str(job.id)[:8]})")
    generate_step = job.steps.filter(step_type='generate').first()
    if generate_step and generate_step.output_asset_id:
        print(f"  Generate Asset: {generate_step.output_asset_id}")
    
    preview_step = job.steps.filter(step_type='preview_export').first()
    if preview_step and preview_step.output_asset_id:
        print(f"  Preview Asset:  {preview_step.output_asset_id}")
