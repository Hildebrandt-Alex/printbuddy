from jobs.models import JobStep

print("=== Cleanup: Löschen von Pending Quick Adjust Steps ohne Assets ===\n")

# Finde alle pending Quick Adjust Steps ohne output_asset_id
orphaned_steps = JobStep.objects.filter(
    step_type='quick_adjust',
    status='pending',
    output_asset_id__isnull=True
)

count = orphaned_steps.count()
print(f"Gefunden: {count} pending Quick Adjust Steps ohne Assets\n")

if count > 0:
    for step in orphaned_steps:
        job_title = step.job.title if step.job else "Unknown"
        print(f"  Löschen: Step {str(step.id)[:8]} (Job: {job_title})")
        print(f"    Order: {step.order}")
        print(f"    Params: {step.params}")
        step.delete()

    print(f"\n✅ {count} Steps gelöscht")
else:
    print("✅ Keine verwaisten Steps gefunden")

# Finale Statistik
print("\n" + "="*60)
print("=== Quick Adjust Status nach Cleanup ===\n")

from jobs.models import Job

jobs = Job.objects.filter(title__in=['test22', 'sdxl', 'maxtest2']).order_by('title')

for job in jobs:
    qa_steps = job.steps.filter(step_type='quick_adjust')
    qa_done = qa_steps.filter(status='done').count()
    qa_pending = qa_steps.filter(status='pending').count()
    
    print(f"Job: {job.title}")
    print(f"  Total Quick Adjusts: {qa_steps.count()}")
    print(f"  Done (mit Assets): {qa_done}")
    print(f"  Pending: {qa_pending}\n")
