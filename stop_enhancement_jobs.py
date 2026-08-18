from jobs.models import Job, JobStep

# Finde alle Enhancement Jobs die in der Queue sind
enhancement_jobs = Job.objects.filter(
    pipeline_template__step_generate=False,
    status__in=['queued', 'running']
).order_by('-created_at')

print(f'=== Enhancement Jobs in Queue: {enhancement_jobs.count()} ===\n')

for job in enhancement_jobs:
    print(f'Job ID: {job.id}')
    print(f'  Title: {job.title}')
    print(f'  Status: {job.status}')
    print(f'  Created: {job.created_at}')
    
    # Zeige Steps mit Errors
    failed_steps = job.steps.filter(status='failed')
    if failed_steps.exists():
        print(f'  Failed Steps: {failed_steps.count()}')
        for step in failed_steps:
            print(f'    {step.step_type}: {step.error_msg[:80]}...')
    
    # Stoppe den Job
    job.status = 'cancelled'
    job.save()
    print(f'  ✅ Job cancelled\n')

print(f'\n✅ Alle {enhancement_jobs.count()} Enhancement Jobs wurden gestoppt')
