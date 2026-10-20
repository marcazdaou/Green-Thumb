"""Server-side cart pricing and checkout.

The browser only ever sends product ids and quantities. Prices and totals are
always looked up here from the database, so a tampered request cannot change
what an order costs.
"""
from decimal import Decimal

from django.db import transaction

from .models import Order, OrderItem, Product

MAX_QUANTITY = 100     # per product line
MAX_LINES = 50         # distinct products per order


class CartError(ValueError):
    """The submitted cart is invalid (unknown product, bad quantity, ...)."""


def parse_items(raw_items) -> dict[int, int]:
    """Validate [{"id": .., "qty": ..}, ...] into {product_id: quantity}.

    Duplicate ids are merged. Raises CartError on anything malformed.
    """
    if not isinstance(raw_items, list) or not raw_items:
        raise CartError("The cart is empty.")
    if len(raw_items) > MAX_LINES:
        raise CartError(f"At most {MAX_LINES} different products per order.")
    quantities: dict[int, int] = {}
    for item in raw_items:
        try:
            product_id, qty = int(item["id"]), int(item["qty"])
        except (KeyError, TypeError, ValueError):
            raise CartError("Each item needs a numeric id and qty.") from None
        if not 1 <= qty <= MAX_QUANTITY:
            raise CartError(f"Quantities must be between 1 and {MAX_QUANTITY}.")
        quantities[product_id] = quantities.get(product_id, 0) + qty
    if any(q > MAX_QUANTITY for q in quantities.values()):
        raise CartError(f"Quantities must be between 1 and {MAX_QUANTITY}.")
    return quantities


def price_cart(quantities: dict[int, int]) -> tuple[list[dict], Decimal]:
    """Look up current prices; return (lines, total). Unknown products are rejected."""
    products = Product.objects.in_bulk(quantities.keys())
    missing = set(quantities) - set(products)
    if missing:
        raise CartError(f"Unknown product id(s): {sorted(missing)}")
    lines = []
    for product_id, qty in quantities.items():
        p = products[product_id]
        lines.append({"product": p, "quantity": qty, "unit_price": p.price, "line_total": p.price * qty})
    return lines, sum((line["line_total"] for line in lines), Decimal("0.00"))


@transaction.atomic
def place_order(quantities: dict[int, int], user=None, status=Order.Status.PLACED) -> Order:
    """Create an Order and its items in one transaction, using server prices."""
    lines, total = price_cart(quantities)
    order = Order.objects.create(user=user if user and user.is_authenticated else None, total=total, status=status)
    OrderItem.objects.bulk_create(
        OrderItem(order=order, product=line["product"], quantity=line["quantity"], unit_price=line["unit_price"])
        for line in lines)
    return order
