from django.conf import settings
import os

print('DJANGO_SETTINGS_MODULE:', os.environ.get('DJANGO_SETTINGS_MODULE'))
print('DATABASE NAME:', settings.DATABASES['default']['NAME'])
print('DATABASE USER:', settings.DATABASES['default']['USER'])
print('DATABASE HOST:', settings.DATABASES['default']['HOST'])

# Try to query job
from jobs.models import Job
print('\n--- Job Count ---')
print(f'Total Jobs: {Job.objects.count()}')

# Try to get the specific job
job_id = 'd0763876-801e-4acb-9189-8e5f87454957'
try:
    job = Job.objects.get(id=job_id)
    print(f'Job found: {job.title}')
except Job.DoesNotExist:
    print(f'Job {job_id} does NOT exist')
    # Show recent jobs
    recent = Job.objects.all().order_by('-created_at')[:5]
    print('\nRecent 5 jobs:')
    for j in recent:
        print(f'  {j.id}: {j.title} - {j.created_at}')
