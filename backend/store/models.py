"""Database schema for the Green Thumb store.

    Product         a real product from the UCI Online Retail II dataset
    Recommendation  "frequently bought together" link between two products,
                    computed by analysis/baskets.py from real orders
    Review          a rating and comment by a signed-in user for one product
    Order           one checkout, with its total computed on the server
    OrderItem       one product line inside an order

Money is stored as Decimal (never float) so totals are exact.
"""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.templatetags.static import static
from django.urls import reverse


class Product(models.Model):
    stock_code = models.CharField(max_length=12, unique=True, help_text="The retailer's product code")
    name = models.CharField(max_length=120)
    category = models.CharField(max_length=40, db_index=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    image = models.CharField(max_length=80, help_text="File name in assets/images/products/")
    # Real sales history from the dataset (Dec 2009 - Dec 2011), shown on the product page.
    historical_customers = models.PositiveIntegerField(default=0)
    historical_orders = models.PositiveIntegerField(default=0)
    historical_units = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-historical_customers", "name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("product_detail", args=[self.pk])

    @property
    def image_url(self) -> str:
        return static(f"images/products/{self.image}")


class Recommendation(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="recommendations")
    recommended = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="+")
    confidence = models.FloatField(help_text="P(recommended in basket | product in basket)")
    lift = models.FloatField(help_text="How many times more often than chance they are bought together")

    class Meta:
        ordering = ["-lift"]
        constraints = [models.UniqueConstraint(fields=["product", "recommended"], name="unique_recommendation")]


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    stars = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    text = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["product", "user"], name="one_review_per_user_per_product"),
            models.CheckConstraint(condition=models.Q(stars__gte=1, stars__lte=5), name="stars_between_1_and_5"),
        ]

    def __str__(self):
        return f"{self.user} on {self.product} ({self.stars}/5)"


class Order(models.Model):
    class Status(models.TextChoices):
        PLACED = "placed", "Placed (no payment)"      # Stripe not configured: order recorded only
        PENDING = "pending", "Awaiting payment"       # sent to Stripe Checkout, not paid yet
        PAID = "paid", "Paid (Stripe test mode)"      # Stripe confirmed the test payment

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name="orders")   # null for guest checkouts
    created_at = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PLACED)
    stripe_session_id = models.CharField(max_length=255, blank=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.pk} (£{self.total}, {self.status})"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_items")
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    # Copied from the product at checkout, so later price changes don't rewrite history.
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)

    @property
    def line_total(self) -> Decimal:
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product}"
