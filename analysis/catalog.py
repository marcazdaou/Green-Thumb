"""Step 2: choose the store's catalog from real products.

Green Thumb sells reusable and garden products, so the catalog is the most
popular items (by number of distinct customers) in three categories of the
real retailer's range, restricted to items still sold in the last quarter of
the data. Prices are the retailer's typical (median) unit price over its last
six months, in British pounds.

Images are real photos, one per product type
(see IMAGE_RULES); they show the kind of product, not the exact item.
"""
import re

import pandas as pd

PER_CATEGORY = 12
ACTIVE_SINCE = "2011-09-01"

# (category, keyword pattern, default image). The first matching category wins.
CATEGORIES = [
    ("Reusable bags",
     r"\b(JUMBO (STORAGE )?BAG|SHOPPER BAG|SHOPPING BAG|CHARLOTTE BAG|RECYCLING BAG|TOTE BAG|JUTE|STORAGE BAG)\b",
     "cottonbag.png"),
    ("Lunch & picnic",
     r"\b(LUNCH BAG|LUNCH BOX|WATER BOTTLE|DRINKING BOTTLE|FLASK|CUTLERY SET|PICNIC (BAG|BASKET))\b",
     "waterbottle.png"),
    ("Garden",
     r"\b(GARDEN|PLANT|PLANTER|WATERING CAN|SEEDS?|HERB|BIRD FEEDER|BIRD ?HOUSE|BIRD TABLE|FLOWER POT|TROWEL)\b",
     "succulet.png"),
]
# Items that match a keyword but are not reusable/garden goods.
EXCLUDE = r"HOT WATER BOTTLE|CHRISTMAS|MARBLES|PARTY BAG|TEA BAG|GIFT BAG|PAPER BAG|CAKE|WRAP|CARD|SIGN|MUG"
# A picture per product *type*, checked in order (most specific first), so a
# lunch bag, a lunch box, a picnic basket and a shopping bag all look different.
# All product images are real photos (credits in assets/images/products/CREDITS.md).
IMAGE_RULES = [
    (r"\bCUTLERY\b", "cutlery.jpg"),
    (r"\bLUNCH BOX\b", "lunchbox.jpg"),
    (r"\b(LUNCH|PICNIC) BAG\b", "lunchbag.jpg"),
    (r"\bPICNIC BASKET\b", "picnic.jpg"),
    (r"\b(WATER|DRINKING) BOTTLE\b", "waterbottle.png"),
    (r"\bJUMBO\b", "jumbobag.jpg"),
    (r"\bWATERING CAN\b", "wateringcan.jpg"),
    (r"\b(ROUNDERS|CROQUET|SKITTLES)\b", "gardengame.jpg"),
    (r"\b(FORK|TROWEL|RAKE|SPADE|SECATEURS)\b", "gardentools.jpg"),
    (r"\b(SEEDS?|HERB)\b", "flowerseeds.png"),
]


def pretty_name(name: str) -> str:
    """'JUMBO BAG  RED RETROSPOT.' -> 'Jumbo Bag Red Retrospot'."""
    words = re.sub(r"\s+", " ", re.sub(r"[.]+$", "", name)).strip().title()
    return re.sub(r"\b(Of|And|With|In)\b", lambda m: m.group(0).lower(), words)


def categorize(name: str) -> tuple[str, str] | None:
    """(category, image) for a product name, or None if it is not a store item."""
    if re.search(EXCLUDE, name):
        return None
    for category, pattern, default_image in CATEGORIES:
        if re.search(pattern, name):
            # Use the first matching product-type picture, else the category's default.
            image = next((img for rule, img in IMAGE_RULES if re.search(rule, name)), default_image)
            return category, image
    return None


def build_catalog(sales: pd.DataFrame) -> pd.DataFrame:
    """One row per catalog product with its real price and sales history."""
    recent_price = (sales[sales["date"] >= sales["date"].max() - pd.DateOffset(months=6)]
                    .groupby("stock_code")["price"].median())
    products = sales.groupby("stock_code").agg(
        name=("description", lambda s: s.dropna().mode().iat[0] if s.notna().any() else ""),
        customers=("customer_id", "nunique"),
        orders=("invoice", "nunique"),
        units=("quantity", "sum"),
        revenue=("revenue", "sum"),
        last_sold=("date", "max"),
    )
    products["price"] = recent_price
    products = products[(products["last_sold"] >= ACTIVE_SINCE) & products["price"].notna()]

    tagged = products["name"].map(categorize)
    products = products[tagged.notna()].copy()
    products[["category", "image"]] = pd.DataFrame(tagged.dropna().tolist(), index=products.index)

    catalog = (products.sort_values("customers", ascending=False)
               .groupby("category", sort=False).head(PER_CATEGORY)
               .reset_index())
    catalog["display_name"] = catalog["name"].map(pretty_name)
    catalog["price"] = catalog["price"].round(2)
    return catalog
