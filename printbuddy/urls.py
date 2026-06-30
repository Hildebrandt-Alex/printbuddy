"""
URL configuration for printbuddy project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Custom Admin-URL aus Settings (niemals /admin/ in Production — ADR Security)
ADMIN_URL = getattr(settings, 'ADMIN_URL', 'pb-manage/')

urlpatterns = [
    path(ADMIN_URL, admin.site.urls),

    # Öffentliche Galerie
    path('gallery/', include('gallery.urls', namespace='gallery')),

    # Studio App (Login-geschützt, Gruppe studio_workers)
    path('studio/login/',  auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('studio/logout/', auth_views.LogoutView.as_view(next_page='/studio/login/'),             name='logout'),
    path('studio/',        include('studio.urls', namespace='studio')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
