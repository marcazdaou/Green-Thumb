"""Fixtures for the website tests: a few products and a signed-in user."""
from decimal import Decimal

import pytest
from django.contrib.auth.models import User

from store.models import Product, Recommendation


@pytest.fixture(autouse=True)
def no_stripe_by_default(settings):
    """Tests run without Stripe unless they turn it on (a local backend/.env must not leak in)."""
    settings.STRIPE_SECRET_KEY = ""
    settings.STRIPE_WEBHOOK_SECRET = ""


@pytest.fixture
def products(db):
    bag = Product.objects.create(stock_code="85099B", name="Jumbo Bag Red Retrospot", category="Reusable bags",
                                 price=Decimal("2.08"), image="cottonbag.png", historical_customers=975)
    lunch = Product.objects.create(stock_code="20725", name="Lunch Bag Red Retrospot", category="Lunch & picnic",
                                   price=Decimal("1.65"), image="waterbottle.png", historical_customers=842)
    ladder = Product.objects.create(stock_code="22487", name="White Wood Garden Plant Ladder", category="Garden",
                                    price=Decimal("9.95"), image="succulet.png", historical_customers=598)
    Recommendation.objects.create(product=bag, recommended=lunch, confidence=0.3, lift=4.2)
    return {"bag": bag, "lunch": lunch, "ladder": ladder}


@pytest.fixture
def user(db):
    return User.objects.create_user("gardener", password="GardenPass123!", first_name="Abc", last_name="Gardener")


@pytest.fixture
def signed_in(client, user):
    client.force_login(user)
    return client
