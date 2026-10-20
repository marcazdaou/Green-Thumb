"""Root URL configuration: admin, the data science dashboard, and the shop."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("insights/", include("insights.urls")),
    path("", include("store.urls")),
]
