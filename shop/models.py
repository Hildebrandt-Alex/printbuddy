import uuid
from django.db import models


class Product(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name        = models.CharField(max_length=100)
    slug        = models.SlugField(unique=True)
    description = models.TextField()
    category    = models.CharField(max_length=40)
    base_image  = models.ImageField(upload_to='shop/products/')
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Produkt'
        verbose_name_plural = 'Produkte'

    def __str__(self):
        return self.name


class ProductVariant(models.Model):
    product                = models.ForeignKey(Product, related_name='variants', on_delete=models.CASCADE)
    size                   = models.CharField(max_length=10)
    color                  = models.CharField(max_length=40)
    printful_variant_id    = models.CharField(max_length=50)
    price_eur              = models.DecimalField(max_digits=8, decimal_places=2)
    cost_eur               = models.DecimalField(max_digits=8, decimal_places=2)
    required_export_types  = models.JSONField(default=list, help_text="z.B. ['pod','cmyk','preview']")
    is_active              = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Produkt-Variante'
        verbose_name_plural = 'Produkt-Varianten'

    def __str__(self):
        return f"{self.product.name} — {self.size} / {self.color}"


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING    = 'pending',    'Ausstehend'
        PAID       = 'paid',       'Bezahlt'
        PROCESSING = 'processing', 'In Bearbeitung'
        SHIPPED    = 'shipped',    'Versendet'
        DELIVERED  = 'delivered',  'Geliefert'
        CANCELLED  = 'cancelled',  'Storniert'

    id                  = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stripe_session_id   = models.CharField(max_length=200, unique=True)
    stripe_payment_id   = models.CharField(max_length=200, blank=True)
    printful_order_id   = models.CharField(max_length=50, blank=True)
    status              = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    email               = models.EmailField()
    name                = models.CharField(max_length=100)
    shipping_address    = models.JSONField(help_text='Von Stripe-Event, nie direkt vom User')
    total_eur           = models.DecimalField(max_digits=10, decimal_places=2)
    tracking_code       = models.CharField(max_length=100, blank=True)
    channel             = models.ForeignKey('channels.SalesChannel', null=True, blank=True, on_delete=models.SET_NULL)
    fulfillment_partner = models.ForeignKey('partners.FulfillmentPartner', null=True, blank=True, on_delete=models.SET_NULL)
    source_channel      = models.CharField(max_length=30, default='shop')
    created_at          = models.DateTimeField(auto_now_add=True)
    updated_at          = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Bestellung'
        verbose_name_plural = 'Bestellungen'

    def __str__(self):
        return f"Order {self.id} — {self.email} [{self.status}]"


class OrderLine(models.Model):
    order    = models.ForeignKey(Order, related_name='lines', on_delete=models.CASCADE)
    variant  = models.ForeignKey(ProductVariant, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    price    = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        verbose_name = 'Bestellposition'
        verbose_name_plural = 'Bestellpositionen'

    def __str__(self):
        return f"{self.order_id} — {self.variant} x{self.quantity}"


class ImageProduct(models.Model):
    class MockupStatus(models.TextChoices):
        PENDING    = 'pending',    'Ausstehend'
        GENERATING = 'generating', 'Wird generiert'
        READY      = 'ready',      'Fertig'
        FAILED     = 'failed',     'Fehlgeschlagen'

    image          = models.ForeignKey('gallery.GalleryImage', on_delete=models.CASCADE, related_name='product_links')
    product        = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='image_links')
    mockup_file    = models.ImageField(upload_to='shop/mockups/', blank=True)
    mockup_status  = models.CharField(max_length=20, choices=MockupStatus.choices, default=MockupStatus.PENDING)
    is_primary     = models.BooleanField(default=False)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('image', 'product')]
        verbose_name = 'Bild-Produkt-Zuordnung'
        verbose_name_plural = 'Bild-Produkt-Zuordnungen'

    def __str__(self):
        return f"{self.image} → {self.product}"

