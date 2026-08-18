from jobs.models import Job

# Suche nach Jobs mit ähnlicher UUID
partial_uuid = 'd0763876'

print('Searching for jobs with UUID starting with:', partial_uuid)
jobs = Job.objects.filter(id__startswith=partial_uuid)
print(f'Found: {jobs.count()} jobs')

if jobs.exists():
    for j in jobs:
        print(f'\nJob ID: {j.id}')
        print(f'Title: {j.title}')
        print(f'Status: {j.status}')
        print(f'Created: {j.created_at}')
else:
    print('\n--- Searching recent jobs ---')
    recent = Job.objects.all().order_by('-created_at')[:10]
    print(f'Found {recent.count()} recent jobs:')
    for j in recent:
        print(f'{j.id}: {j.title} - {j.status} - {j.created_at}')
