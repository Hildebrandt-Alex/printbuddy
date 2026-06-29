from django.contrib import admin
from .models import PrintBundle


@admin.register(PrintBundle)
class PrintBundleAdmin(admin.ModelAdmin):
    list_display  = ('id', 'order', 'format', 'status', 'created_at')
    list_filter   = ('status', 'format')
    readonly_fields = ('created_at',)

