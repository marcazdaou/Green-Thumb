"""Stripe Checkout (test mode). Stripe's API is replaced by fakes; webhook signatures are real."""
import hashlib
import hmac
import json
import time
from decimal import Decimal

import pytest
import stripe
from django.core.exceptions import ImproperlyConfigured

from store import payments
from store.models import Order

WEBHOOK_SECRET = "whsec_test_secret"


@pytest.fixture
def stripe_on(settings):
    settings.STRIPE_SECRET_KEY = "sk_test_fake"
    settings.STRIPE_WEBHOOK_SECRET = WEBHOOK_SECRET


@pytest.fixture
def fake_create(monkeypatch):
    """Record what we send to Stripe and return a fake hosted-checkout session."""
    calls = []

    def create(**params):
        calls.append(params)
        return {"id": "cs_test_123", "url": "https://checkout.stripe.com/c/pay/cs_test_123"}
    monkeypatch.setattr(stripe.checkout.Session, "create", create)
    return calls


def checkout(client, items):
    return client.post("/api/checkout/", data=json.dumps({"items": items}), content_type="application/json")


def signed(payload: dict, secret=WEBHOOK_SECRET):
    """Sign a webhook body exactly like Stripe does (HMAC-SHA256 of "timestamp.body")."""
    body = json.dumps(payload)
    ts = int(time.time())
    sig = hmac.new(secret.encode(), f"{ts}.{body}".encode(), hashlib.sha256).hexdigest()
    return body, f"t={ts},v1={sig}"


def completed_event(order, payment_status="paid"):
    return {"type": "checkout.session.completed", "data": {"object": {
        "id": order.stripe_session_id, "payment_status": payment_status,
        "metadata": {"order_id": str(order.pk)}}}}


def test_checkout_sends_server_prices_to_stripe(client, products, stripe_on, fake_create):
    response = checkout(client, [{"id": products["bag"].pk, "qty": 3, "price": 0.01}])
    assert response.status_code == 201
    assert response.json()["checkout_url"].startswith("https://checkout.stripe.com/")
    order = Order.objects.get()
    assert (order.status, order.stripe_session_id, order.total) == ("pending", "cs_test_123", Decimal("6.24"))
    line = fake_create[0]["line_items"][0]
    assert line["quantity"] == 3
    assert line["price_data"] == {"currency": "gbp", "unit_amount": 208,     # £2.08 in pence, from the database
                                  "product_data": {"name": "Jumbo Bag Red Retrospot"}}
    assert fake_create[0]["api_key"] == "sk_test_fake"


def test_without_stripe_orders_are_recorded_without_payment(client, products, fake_create):
    response = checkout(client, [{"id": products["bag"].pk, "qty": 1}])
    assert "checkout_url" not in response.json()
    assert Order.objects.get().status == "placed"
    assert fake_create == []


def test_live_keys_are_refused(settings):
    settings.STRIPE_SECRET_KEY = "sk_live_real_money"
    with pytest.raises(ImproperlyConfigured):
        payments.enabled()


def test_stripe_outage_leaves_no_order(client, products, stripe_on, monkeypatch):
    def fail(**params):
        raise stripe.APIConnectionError("network down")
    monkeypatch.setattr(stripe.checkout.Session, "create", fail)
    response = checkout(client, [{"id": products["bag"].pk, "qty": 1}])
    assert response.status_code == 502
    assert Order.objects.count() == 0


def test_valid_webhook_marks_order_paid(client, products, stripe_on, fake_create):
    checkout(client, [{"id": products["bag"].pk, "qty": 1}])
    order = Order.objects.get()
    body, signature = signed(completed_event(order))
    response = client.post("/stripe/webhook/", data=body, content_type="application/json",
                           HTTP_STRIPE_SIGNATURE=signature)
    assert response.status_code == 200
    order.refresh_from_db()
    assert order.status == "paid"


def test_forged_webhook_is_rejected(client, products, stripe_on, fake_create):
    checkout(client, [{"id": products["bag"].pk, "qty": 1}])
    order = Order.objects.get()
    body, signature = signed(completed_event(order), secret="whsec_attacker")
    response = client.post("/stripe/webhook/", data=body, content_type="application/json",
                           HTTP_STRIPE_SIGNATURE=signature)
    assert response.status_code == 400
    order.refresh_from_db()
    assert order.status == "pending"


def test_session_cannot_pay_a_different_order(products, stripe_on):
    order = Order.objects.create(total=Decimal("2.08"), status="pending", stripe_session_id="cs_test_mine")
    assert payments.mark_paid({"id": "cs_test_other", "payment_status": "paid",
                               "metadata": {"order_id": str(order.pk)}}) is None
    order.refresh_from_db()
    assert order.status == "pending"


@pytest.mark.parametrize("payment_status, shown", [("paid", "Payment received"), ("unpaid", "Payment not confirmed")])
def test_success_page_trusts_stripe_not_the_url(client, products, stripe_on, monkeypatch, payment_status, shown):
    order = Order.objects.create(total=Decimal("2.08"), status="pending", stripe_session_id="cs_test_123")
    # A real StripeObject (not a dict), exactly the type the Stripe library returns.
    monkeypatch.setattr(stripe.checkout.Session, "retrieve", lambda session_id, **kw: stripe.StripeObject.construct_from(
        {"id": session_id, "payment_status": payment_status, "metadata": {"order_id": str(order.pk)}}, "sk_test_fake"))
    response = client.get("/checkout/success/?session_id=cs_test_123")
    assert shown in response.content.decode()
    order.refresh_from_db()
    assert order.status == ("paid" if payment_status == "paid" else "pending")


def test_pending_orders_are_not_counted_on_the_dashboard(products):
    from insights.views import store_activity
    Order.objects.create(total=Decimal("5.00"), status="paid")
    Order.objects.create(total=Decimal("9.00"), status="pending")
    activity = store_activity()
    assert (activity["orders"], activity["revenue"]) == (1, Decimal("5.00"))
