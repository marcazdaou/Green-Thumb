"""
urls.py
Maps URL paths to view functions for the store app.

All routes are mounted at the site root via include('store.urls') in
greenthumb/urls.py, so the paths listed here are the final public URLs.
"""

from django.urls import path
from . import views

urlpatterns = [
    # ── Public pages ──────────────────────────────────────────────────────────
    path('',            views.home_view,      name='home'),
    path('shop/',       views.shop_view,      name='shop'),
    path('reviews/',    views.reviews_view,   name='reviews'),
    path('about/',      views.about_view,     name='about'),
    path('cart/',       views.cart_view,      name='cart'),
    path('analytics/',  views.analytics_view, name='analytics'),

    # ── Review API ────────────────────────────────────────────────────────────
    # POST — submit a new review (login required)
    path('reviews/submit/',                    views.submit_review_view, name='submit_review'),
    # POST — delete a specific review by its database ID (owner only)
    path('reviews/delete/<int:review_id>/',    views.delete_review_view, name='delete_review'),

    # ── Order API ─────────────────────────────────────────────────────────────
    # POST — records cart items to the database when a checkout is completed
    path('orders/submit/', views.submit_order_view, name='submit_order'),

    # ── Authentication ────────────────────────────────────────────────────────
    path('register/', views.register_view, name='register'),
    path('login/',    views.login_view,    name='login'),
    path('logout/',   views.logout_view,   name='logout'),
]
