"""Every page renders, shop filtering works, and the dashboard shows real results."""
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.db.models import F

from insights.views import store_activity
from store.models import Order, Product, Recommendation


@pytest.mark.parametrize("url", ["/", "/shop/", "/cart/", "/reviews/", "/about/", "/login/", "/register/", "/insights/"])
def test_pages_render(client, products, url):
    assert client.get(url).status_code == 200


def test_shop_filters_by_category_and_search(client, products):
    garden = client.get("/shop/?category=Garden").context["products"]
    assert [p.name for p in garden] == ["White Wood Garden Plant Ladder"]
    found = client.get("/shop/?q=lunch").context["products"]
    assert [p.name for p in found] == ["Lunch Bag Red Retrospot"]


def test_shop_sorts_by_price(client, products):
    prices = [p.price for p in client.get("/shop/?sort=price_low").context["products"]]
    assert prices == sorted(prices)


def test_product_page_shows_recommendations(client, products):
    response = client.get(f"/shop/{products['bag'].pk}/")
    assert [r.recommended for r in response.context["recommendations"]] == [products["lunch"]]
    assert client.get("/shop/99999/").status_code == 404


def test_dashboard_shows_findings_from_results(client, products):
    html = client.get("/insights/").content.decode()
    assert "Champions" in html and "ROC AUC" in html


def test_store_activity_months_are_chronological(db, products):
    """The old dashboard sorted "Apr 2026" before "Jan 2026"; months must be in time order."""
    for month in (4, 1, 2):
        order = Order.objects.create(total=Decimal("1.00"))
        Order.objects.filter(pk=order.pk).update(created_at=datetime(2026, month, 15, tzinfo=timezone.utc))
    assert [m["month"] for m in store_activity()["by_month"]] == ["2026-01", "2026-02", "2026-04"]


def test_load_catalog_command_is_idempotent(db):
    call_command("load_catalog")
    call_command("load_catalog")
    assert Product.objects.count() == 36
    assert Recommendation.objects.exists()
    assert not Recommendation.objects.filter(product=F("recommended")).exists()   # never recommends itself
