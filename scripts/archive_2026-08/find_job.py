from jobs.models import Job

# Suche nach Jobs  mit ähnlicher UUID
job_id_partial = 'd0763876'

jobs = Job.objects.filter(id__startswith=job_id_partial)
print(f'Jobs mit UUID starting with {job_id_partial}: {jobs.count()}')

# Zeige letzte 10 Jobs
print('\n--- Letzte 10 Jobs ---')
recent_jobs = Job.objects.all().order_by('-created_at')[:10]
for j in recent_jobs:
    print(f'{j.id}: {j.title} - {j.status} - {j.created_at}')
