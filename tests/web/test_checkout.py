"""Server-side pricing: the browser can never set what an order costs."""
import json
from decimal import Decimal

import pytest

from store.cart import CartError, parse_items
from store.models import Order


def post(client, url, payload):
    return client.post(url, data=json.dumps(payload), content_type="application/json")


def test_checkout_uses_database_prices_not_the_request(client, products):
    # A tampered request with a fake price and total: both must be ignored.
    payload = {"items": [{"id": products["ladder"].pk, "qty": 2, "price": 0.01}], "total": 0.02}
    response = post(client, "/api/checkout/", payload)
    assert response.status_code == 201
    order = Order.objects.get(pk=response.json()["order_id"])
    assert order.total == Decimal("19.90")                    # 2 x £9.95 from the database
    assert order.items.get().unit_price == Decimal("9.95")


def test_cart_api_prices_and_totals(client, products):
    payload = {"items": [{"id": products["bag"].pk, "qty": 3}, {"id": products["lunch"].pk, "qty": 1}]}
    data = post(client, "/api/cart/", payload).json()
    assert data["total"] == "7.89"                              # 3 x 2.08 + 1.65, exact decimal
    assert {line["name"] for line in data["lines"]} == {"Jumbo Bag Red Retrospot", "Lunch Bag Red Retrospot"}


@pytest.mark.parametrize("items", [
    [], [{"id": 1, "qty": 0}], [{"id": 1, "qty": 101}], [{"id": "x", "qty": 1}], [{"qty": 1}], "not a list",
])
def test_invalid_carts_are_rejected(items):
    with pytest.raises(CartError):
        parse_items(items)


def test_duplicate_lines_are_merged_and_capped():
    assert parse_items([{"id": 5, "qty": 40}, {"id": 5, "qty": 10}]) == {5: 50}
    with pytest.raises(CartError):
        parse_items([{"id": 5, "qty": 60}, {"id": 5, "qty": 60}])


def test_unknown_product_creates_no_order(client, products):
    response = post(client, "/api/checkout/", {"items": [{"id": products["bag"].pk, "qty": 1}, {"id": 99999, "qty": 1}]})
    assert response.status_code == 400
    assert Order.objects.count() == 0                            # the whole order is rejected (transaction)


def test_checkout_records_the_signed_in_user(signed_in, user, products):
    response = post(signed_in, "/api/checkout/", {"items": [{"id": products["bag"].pk, "qty": 1}]})
    assert Order.objects.get(pk=response.json()["order_id"]).user == user


def test_cart_page_provides_the_csrf_token_the_api_needs(products):
    """With CSRF checks on (as in a real browser), the cart page must hand out the token."""
    from django.test import Client
    browser = Client(enforce_csrf_checks=True)
    payload = json.dumps({"items": [{"id": products["bag"].pk, "qty": 1}]})
    assert browser.post("/api/cart/", payload, content_type="application/json").status_code == 403
    token = browser.get("/cart/").cookies["csrftoken"].value
    response = browser.post("/api/cart/", payload, content_type="application/json", HTTP_X_CSRFTOKEN=token)
    assert response.status_code == 200


def test_checkout_rejects_get_and_bad_json(client, products):
    assert client.get("/api/checkout/").status_code == 405
    assert client.post("/api/checkout/", data="{oops", content_type="application/json").status_code == 400
