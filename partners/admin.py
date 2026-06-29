from django.contrib import admin
from .models import FulfillmentPartner, PartnerProduct, PartnerVariant


class PartnerProductInline(admin.TabularInline):
    model = PartnerProduct
    extra = 0


@admin.register(FulfillmentPartner)
class FulfillmentPartnerAdmin(admin.ModelAdmin):
    list_display  = ('name', 'contact_name', 'email', 'is_active', 'created_at')
    list_filter   = ('is_active',)
    search_fields = ('name', 'email', 'contact_name')
    inlines       = [PartnerProductInline]


@admin.register(PartnerVariant)
class PartnerVariantAdmin(admin.ModelAdmin):
    list_display  = ('partner', 'variant', 'partner_sku', 'is_available')
    list_filter   = ('is_available', 'partner')
    search_fields = ('partner_sku',)

