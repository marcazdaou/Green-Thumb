"""Remove the original demo tables.

The first version stored made-up products keyed by name, and reviews/orders
that referenced products by free text. They are replaced in 0007 by a real
catalog with proper foreign keys. The old rows were test data only.
"""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("store", "0005_orderitem")]

    operations = [
        migrations.DeleteModel(name="OrderItem"),
        migrations.DeleteModel(name="Review"),
        migrations.DeleteModel(name="ShopProduct"),
    ]
