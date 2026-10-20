"""Registers the Store app (catalog, cart, orders, reviews, accounts) with Django."""
from django.apps import AppConfig


class StoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'store'
