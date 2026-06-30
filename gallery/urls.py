from django.urls import path

from .views import GalleryDetailView, GalleryListView

app_name = "gallery"

urlpatterns = [
    path("",          GalleryListView.as_view(),  name="list"),
    path("<slug:slug>/", GalleryDetailView.as_view(), name="detail"),
]
