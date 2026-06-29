import uuid
from django.db import models


class SalesChannel(models.Model):
    class ChannelType(models.TextChoices):
        OWN_SHOP   = 'own_shop',   'Eigener Shop'
        ETSY       = 'etsy',       'Etsy'
        WOOCOMMERCE = 'woocommerce', 'WooCommerce'
        SHOPIFY    = 'shopify',    'Shopify'
        MANUAL     = 'manual',     'Manuell'

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name         = models.CharField(max_length=100)
    channel_type = models.CharField(max_length=20, choices=ChannelType.choices)
    is_active    = models.BooleanField(default=True)
    webhook_url  = models.CharField(max_length=500, blank=True)
    api_key      = models.CharField(max_length=200, blank=True, help_text='Verschlüsselt in DB')
    api_secret   = models.CharField(max_length=200, blank=True, help_text='Verschlüsselt in DB')
    base_url     = models.URLField(blank=True, help_text='Für WooCommerce, Shopify etc.')
    notes        = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Vertriebskanal'
        verbose_name_plural = 'Vertriebskanäle'

    def __str__(self):
        return f"{self.name} ({self.channel_type})"

