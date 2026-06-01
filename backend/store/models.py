"""
models.py
Defines the database schema for the Green Thumb store.

Tables:
    ShopProduct  — products shown in the shop
    Review       — customer reviews submitted through the site
    OrderItem    — individual line items recorded when a cart is checked out
"""

from django.db import models
from django.conf import settings


class ShopProduct(models.Model):
    """
    Represents a single product in the shop catalog.

    product_name is the primary key so that it can be referenced by name
    in reviews and orders without a separate integer ID.
    """
    product_name = models.CharField(max_length=30,  name="product_name", primary_key=True)
    desc         = models.CharField(max_length=150, name="desc")
    price        = models.FloatField(name="price")
    src          = models.CharField()   # URL or path to the product image

    def __str__(self):
        return self.product_name


class Review(models.Model):
    """
    Represents a customer review tied to a specific product.

    The user field is nullable so that reviews are not lost if the account
    that wrote them is later deleted.
    """
    user       = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    name       = models.CharField(max_length=100)   # display name entered by the reviewer
    product    = models.CharField(max_length=100)   # product name the review is for
    stars      = models.IntegerField()              # rating from 1 to 5
    text       = models.TextField()                 # review body
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} — {self.product} ({self.stars}★)"


class OrderItem(models.Model):
    """
    Records a single product line from a completed cart checkout.

    When a customer clicks 'Place Order', the frontend POSTs each cart item
    to /orders/submit/ and Django creates one OrderItem per product.
    This gives us real purchase data to analyse in the analytics dashboard.
    """
    product_name = models.CharField(max_length=100)
    unit_price   = models.FloatField()              # price per single unit at time of purchase
    quantity     = models.IntegerField(default=1)   # how many units were bought
    total        = models.FloatField()              # unit_price * quantity
    purchased_at = models.DateTimeField(auto_now_add=True)
    user         = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True                       # null when purchased as guest
    )

    def __str__(self):
        return f"{self.product_name} x{self.quantity} (${self.total:.2f})"
