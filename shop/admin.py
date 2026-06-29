from django.contrib import admin
from .models import Product, ProductVariant, Order, OrderLine, ImageProduct


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0


class OrderLineInline(admin.TabularInline):
    model = OrderLine
    extra = 0
    readonly_fields = ('price',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display  = ('name', 'category', 'is_active', 'created_at')
    list_filter   = ('category', 'is_active')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    inlines       = [ProductVariantInline]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display  = ('id', 'email', 'name', 'status', 'total_eur', 'source_channel', 'created_at')
    list_filter   = ('status', 'source_channel')
    search_fields = ('email', 'name', 'stripe_session_id', 'printful_order_id')
    readonly_fields = ('stripe_session_id', 'stripe_payment_id', 'created_at', 'updated_at')
    inlines       = [OrderLineInline]


@admin.register(ImageProduct)
class ImageProductAdmin(admin.ModelAdmin):
    list_display  = ('image', 'product', 'mockup_status', 'is_primary', 'created_at')
    list_filter   = ('mockup_status', 'is_primary')

