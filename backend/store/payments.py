"""Stripe Checkout in *test mode*: a real payment integration that never moves real money.

How a payment works:
1. checkout_api saves the order as "pending" (prices from the database, see cart.py).
2. create_checkout_session() asks Stripe for a hosted payment page for exactly
   those lines and sends the shopper there. Card details are typed on Stripe's
   page, so this site never sees or stores a card number.
3. Stripe confirms the payment twice, and either one marks the order "paid":
   - the shopper returns to /checkout/success/ (we re-check the session with Stripe);
   - Stripe calls /stripe/webhook/ (signature-verified), even if the shopper closed the tab.

Safety: only Stripe *test* keys are accepted. A live key raises an error, so this
portfolio site can never charge a real card. Without a key, checkout falls back
to recording the order with no payment step.
"""
import json
from decimal import Decimal

import stripe
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse

from .models import Order

TEST_CARD = "4242 4242 4242 4242"   # Stripe's public test card number


def _api_key() -> str:
    """The configured Stripe secret key, refusing anything that is not a test key."""
    key = settings.STRIPE_SECRET_KEY
    if key and not key.startswith(("sk_test_", "rk_test_")):
        raise ImproperlyConfigured("Only Stripe test keys (sk_test_...) are allowed: this site must not take real payments.")
    return key


def enabled() -> bool:
    """True when a Stripe test key is configured."""
    return bool(_api_key())


def to_pence(amount: Decimal) -> int:
    """Stripe expects whole minor units: £2.08 -> 208."""
    return int((amount * 100).quantize(Decimal("1")))


def create_checkout_session(order: Order, request) -> str:
    """Create a Stripe Checkout page for a pending order and return its URL."""
    items = order.items.select_related("product")
    session = stripe.checkout.Session.create(
        api_key=_api_key(),
        mode="payment",
        line_items=[{
            "quantity": item.quantity,
            "price_data": {"currency": "gbp", "unit_amount": to_pence(item.unit_price),
                           "product_data": {"name": item.product.name}},
        } for item in items],
        client_reference_id=str(order.pk),
        metadata={"order_id": str(order.pk)},
        # Stripe replaces {CHECKOUT_SESSION_ID} with the real id when it redirects back.
        success_url=request.build_absolute_uri(reverse("checkout_success")) + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=request.build_absolute_uri(reverse("cart")),
    )
    order.stripe_session_id = session["id"]
    order.save(update_fields=["stripe_session_id"])
    return session["url"]


def mark_paid(session) -> Order | None:
    """Mark the session's order as paid if Stripe says it is. Safe to call more than once.

    The order must match both the id in the metadata and the session id we saved,
    so a session for one order can never mark a different order as paid.
    """
    order = Order.objects.filter(pk=(session.get("metadata") or {}).get("order_id"),
                                 stripe_session_id=session.get("id")).first()
    if order and session.get("payment_status") == "paid" and order.status != Order.Status.PAID:
        order.status = Order.Status.PAID
        order.save(update_fields=["status"])
    return order


def confirm_from_redirect(session_id: str) -> Order | None:
    """Shopper came back from Stripe: fetch the session from Stripe (never trust the URL alone)."""
    session = stripe.checkout.Session.retrieve(session_id, api_key=_api_key())
    return mark_paid(session.to_dict() if hasattr(session, "to_dict") else session)   # plain dict, like a webhook


def handle_webhook(payload: bytes, signature: str | None) -> None:
    """Verify a webhook really comes from Stripe, then record completed payments.

    Raises stripe.SignatureVerificationError (or ValueError) for anything forged or malformed.
    """
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise ValueError("STRIPE_WEBHOOK_SECRET is not set.")
    stripe.WebhookSignature.verify_header(payload, signature, settings.STRIPE_WEBHOOK_SECRET, 300)
    event = json.loads(payload)
    if event.get("type") in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
        mark_paid(event["data"]["object"])
