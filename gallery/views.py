from django.shortcuts import get_object_or_404, render
from django.views.generic import DetailView, ListView

from .models import GalleryImage


class GalleryListView(ListView):
    model = GalleryImage
    template_name = "gallery/list.html"
    context_object_name = "images"
    paginate_by = 24

    def get_queryset(self):
        qs = GalleryImage.objects.filter(is_public=True)
        cat = self.request.GET.get("cat", "")
        if cat:
            qs = qs.filter(category=cat)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cat_filter"] = self.request.GET.get("cat", "")
        ctx["categories"] = GalleryImage.Category.choices
        return ctx


class GalleryDetailView(DetailView):
    model = GalleryImage
    template_name = "gallery/detail.html"
    context_object_name = "image"

    def get_queryset(self):
        return GalleryImage.objects.filter(is_public=True)

