import uuid
from django.db import models


class PrintBundle(models.Model):
    class Format(models.TextChoices):
        ZIP    = 'zip',    'ZIP-Archiv'
        FOLDER = 'folder', 'Ordner'

    class Status(models.TextChoices):
        PENDING   = 'pending',   'Ausstehend'
        BUILDING  = 'building',  'Wird erstellt'
        READY     = 'ready',     'Fertig'
        DELIVERED = 'delivered', 'Ausgeliefert'

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order       = models.ForeignKey('shop.Order', on_delete=models.CASCADE)
    asset_ids   = models.JSONField(default=list)
    bundle_path = models.CharField(max_length=500, blank=True)
    format      = models.CharField(max_length=10, choices=Format.choices, default=Format.ZIP)
    status      = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Print-Bundle'
        verbose_name_plural = 'Print-Bundles'

    def __str__(self):
        return f"Bundle {self.id} [{self.status}]"

