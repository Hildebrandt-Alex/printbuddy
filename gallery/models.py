import uuid
from django.db import models
from PIL import Image as PilImage
import io
from django.core.files.base import ContentFile


class GalleryImage(models.Model):
    class Category(models.TextChoices):
        SHIRT  = 'shirt',  'T-Shirt'
        POSTER = 'poster', 'Poster'
        CARD   = 'card',   'Grußkarte'
        ART    = 'art',    'Kunstdruck'

    class CTAType(models.TextChoices):
        ETSY    = 'etsy',    'Etsy'
        SHOP    = 'shop',    'Eigener Shop'
        CONTACT = 'contact', 'Kontakt'

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title       = models.CharField(max_length=120)
    slug        = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    project     = models.ForeignKey('jobs.Project', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='gallery_images', help_text="Projekt-Zuordnung (optional)")
    file_path   = models.ImageField(upload_to='gallery/full/')
    thumb_path  = models.ImageField(upload_to='gallery/thumbs/', blank=True)
    category    = models.CharField(max_length=20, choices=Category.choices)
    tags        = models.CharField(max_length=250, blank=True, help_text='Kommasepariert')
    cta_type    = models.CharField(max_length=20, choices=CTAType.choices, default=CTAType.SHOP)
    cta_url     = models.URLField(blank=True)
    is_public   = models.BooleanField(default=False)
    sort_order  = models.PositiveIntegerField(default=0)
    source_job_id = models.UUIDField(null=True, blank=True, help_text='Loses Coupling — kein FK')
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', '-created_at']
        verbose_name = 'Galerie-Bild'
        verbose_name_plural = 'Galerie-Bilder'

    def __str__(self):
        return self.title

    def _generate_thumbnail(self):
        """600x600 JPEG Thumbnail via Pillow."""
        if not self.file_path:
            return
        img = PilImage.open(self.file_path)
        img = img.convert('RGB')
        img.thumbnail((600, 600), PilImage.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=85)
        fname = f"{self.slug}_thumb.jpg"
        self.thumb_path.save(fname, ContentFile(buf.getvalue()), save=False)

    def save(self, *args, **kwargs):
        generating_thumb = bool(self.file_path and not self.thumb_path)
        if generating_thumb:
            self._generate_thumbnail()
        super().save(*args, **kwargs)

