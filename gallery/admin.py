from django.contrib import admin
from .models import GalleryImage


@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display  = ('title', 'category', 'cta_type', 'is_public', 'sort_order', 'created_at')
    list_filter   = ('category', 'cta_type', 'is_public')
    search_fields = ('title', 'slug', 'tags')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('thumb_path', 'created_at', 'updated_at')
    list_editable = ('is_public', 'sort_order')

