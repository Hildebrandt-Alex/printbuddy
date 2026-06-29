import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class FulfillmentPartner(models.Model):
    id                  = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name                = models.CharField(max_length=100)
    user                = models.OneToOneField(User, on_delete=models.PROTECT)
    email               = models.EmailField()
    contact_name        = models.CharField(max_length=100)
    export_formats      = models.JSONField(default=list, help_text="['pod','cmyk','vector']")
    notify_email        = models.BooleanField(default=True)
    notify_webhook_url  = models.CharField(max_length=500, blank=True)
    notes               = models.TextField(blank=True)
    is_active           = models.BooleanField(default=True)
    created_at          = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Fulfillment-Partner'
        verbose_name_plural = 'Fulfillment-Partner'

    def __str__(self):
        return self.name


class PartnerProduct(models.Model):
    partner      = models.ForeignKey(FulfillmentPartner, on_delete=models.CASCADE)
    product      = models.ForeignKey('shop.Product', on_delete=models.CASCADE)
    export_types = models.JSONField(default=list)
    notes        = models.TextField(blank=True)

    class Meta:
        unique_together = [('partner', 'product')]
        verbose_name = 'Partner-Produkt'
        verbose_name_plural = 'Partner-Produkte'

    def __str__(self):
        return f"{self.partner} — {self.product}"


class PartnerVariant(models.Model):
    partner      = models.ForeignKey(FulfillmentPartner, on_delete=models.CASCADE)
    variant      = models.ForeignKey('shop.ProductVariant', on_delete=models.CASCADE)
    partner_sku  = models.CharField(max_length=100, blank=True)
    is_available = models.BooleanField(default=True)
    notes        = models.TextField(blank=True)

    class Meta:
        unique_together = [('partner', 'variant')]
        verbose_name = 'Partner-Variante'
        verbose_name_plural = 'Partner-Varianten'

    def __str__(self):
        return f"{self.partner} — {self.variant}"

