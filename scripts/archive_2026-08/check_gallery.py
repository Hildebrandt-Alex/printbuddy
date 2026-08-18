#!/usr/bin/env python
"""
Check GalleryImages in database.
"""
from gallery.models import GalleryImage

print("\n=== GalleryImages in DB ===\n")
images = GalleryImage.objects.all().order_by('-created_at')[:10]

print(f"Total: {GalleryImage.objects.count()}")
print(f"Public: {GalleryImage.objects.filter(is_public=True).count()}\n")

for img in images:
    print(f"{img.title}")
    print(f"  Slug: {img.slug}")
    print(f"  Public: {img.is_public}")
    print(f"  Category: {img.category}")
    print(f"  file_path: {img.file_path}")
    print(f"  thumb_path: {img.thumb_path}")
    print(f"  source_job_id: {img.source_job_id}")
    print()
