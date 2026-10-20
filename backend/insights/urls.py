"""URL route for the Insights dashboard (mounted at /insights/ in greenthumb/urls.py)."""
from django.urls import path

from . import views

urlpatterns = [path("", views.dashboard_view, name="insights")]
