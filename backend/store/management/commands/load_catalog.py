"""python manage.py load_catalog

Loads store/data/catalog.json (written by `python -m analysis.run_pipeline`)
into the database: real products, real prices and "frequently bought
together" recommendations. Safe to run repeatedly: products are matched by
stock code and updated in place, and recommendations are rebuilt.
"""
import json
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from store.models import Product, Recommendation

CATALOG = Path(__file__).resolve().parents[2] / "data" / "catalog.json"


class Command(BaseCommand):
    help = "Load the real product catalog and recommendations from store/data/catalog.json"

    @transaction.atomic
    def handle(self, *args, **options):
        data = json.loads(CATALOG.read_text(encoding="utf-8"))
        products = {}
        for p in data["products"]:
            products[p["stock_code"]], _ = Product.objects.update_or_create(
                stock_code=p["stock_code"],
                defaults={"name": p["name"], "category": p["category"], "image": p["image"],
                          "price": Decimal(str(p["price"])), "historical_customers": p["customers"],
                          "historical_orders": p["orders"], "historical_units": p["units_sold"]})

        Recommendation.objects.all().delete()
        Recommendation.objects.bulk_create(
            Recommendation(product=products[p["stock_code"]], recommended=products[r["stock_code"]],
                           confidence=r["confidence"], lift=r["lift"])
            for p in data["products"] for r in p["recommendations"] if r["stock_code"] in products)

        self.stdout.write(self.style.SUCCESS(
            f"Loaded {len(products)} products and {Recommendation.objects.count()} recommendations."))
