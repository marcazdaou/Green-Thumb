"""Admin panel (/admin): lets a staff account browse and manage products, reviews and orders.

Order totals and line prices are read-only here, so they always match what the
server charged at checkout.
"""
from django.contrib import admin

from .models import Order, OrderItem, Product, Recommendation, Review


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "stock_code", "category", "price", "historical_customers")
    list_filter = ("category",)
    search_fields = ("name", "stock_code")


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ("product", "recommended", "confidence", "lift")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "stars", "created_at")
    list_filter = ("stars",)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "quantity", "unit_price")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "total", "status", "created_at")
    list_filter = ("status",)
    inlines = [OrderItemInline]
    readonly_fields = ("total", "status", "stripe_session_id")   # set by checkout / Stripe only
