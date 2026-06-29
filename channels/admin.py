from django.contrib import admin
from .models import SalesChannel


@admin.register(SalesChannel)
class SalesChannelAdmin(admin.ModelAdmin):
    list_display  = ('name', 'channel_type', 'is_active', 'created_at')
    list_filter   = ('channel_type', 'is_active')
    search_fields = ('name',)
    list_editable = ('is_active',)

