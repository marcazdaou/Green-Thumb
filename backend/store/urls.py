"""URL routes for the shop: each address on the site points to a function in views.py."""
from django.urls import path

from . import views

urlpatterns = [
    # Pages
    path("", views.home_view, name="home"),
    path("shop/", views.shop_view, name="shop"),
    path("shop/<int:pk>/", views.product_detail_view, name="product_detail"),
    path("cart/", views.cart_view, name="cart"),
    path("reviews/", views.reviews_view, name="reviews"),
    path("about/", views.about_view, name="about"),
    # JSON API used by cart.js
    path("api/cart/", views.cart_api, name="cart_api"),
    path("api/checkout/", views.checkout_api, name="checkout_api"),
    # Stripe (test mode): return page after paying, and Stripe's server-to-server webhook
    path("checkout/success/", views.checkout_success_view, name="checkout_success"),
    path("stripe/webhook/", views.stripe_webhook, name="stripe_webhook"),
    # Reviews (HTML form posts)
    path("reviews/submit/", views.submit_review_view, name="submit_review"),
    path("reviews/<int:review_id>/delete/", views.delete_review_view, name="delete_review"),
    # Accounts
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
]
