"""Registers the Insights app (the data science dashboard) with Django."""
from django.apps import AppConfig


class InsightsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "insights"
    verbose_name = "Data science insights"
