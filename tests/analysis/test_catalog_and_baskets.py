"""Catalog selection rules and market basket arithmetic."""
import pandas as pd
import pytest

from analysis import baskets
from analysis.catalog import categorize, pretty_name


@pytest.mark.parametrize("name, expected", [
    ("JUMBO BAG RED RETROSPOT", ("Reusable bags", "jumbobag.jpg")),
    ("RED RETROSPOT SHOPPER BAG", ("Reusable bags", "cottonbag.png")),
    ("LUNCH BAG CARS BLUE", ("Lunch & picnic", "lunchbag.jpg")),
    ("SPACEBOY LUNCH BOX", ("Lunch & picnic", "lunchbox.jpg")),
    ("STRAWBERRY LUNCH BOX WITH CUTLERY", ("Lunch & picnic", "cutlery.jpg")),
    ("PICNIC BASKET WICKER LARGE", ("Lunch & picnic", "picnic.jpg")),
    ("WATERING CAN BLUE ELEPHANT", ("Garden", "wateringcan.jpg")),
    ("WOODEN CROQUET GARDEN SET", ("Garden", "gardengame.jpg")),
    ("CHILDS GARDEN FORK BLUE", ("Garden", "gardentools.jpg")),
    ("WHITE WOOD GARDEN PLANT LADDER", ("Garden", "succulet.png")),
    ("SET OF 6 HERB TINS SKETCHBOOK", ("Garden", "flowerseeds.png")),
    ("CHOCOLATE HOT WATER BOTTLE", None),        # "water bottle", but not a reusable drinks bottle
    ("POTTING SHED TEA MUG", None),              # excluded keyword
    ("PAPER CHAIN KIT 50'S CHRISTMAS", None),
])
def test_categorize(name, expected):
    assert categorize(name) == expected


def test_pretty_name():
    assert pretty_name("LUNCH BAG  BLACK SKULL.") == "Lunch Bag Black Skull"
    assert pretty_name("STRAWBERRY LUNCH BOX WITH CUTLERY") == "Strawberry Lunch Box with Cutlery"


def test_association_rule_arithmetic(monkeypatch):
    """Four baskets with known counts: A&B together in 2 of them."""
    monkeypatch.setattr(baskets, "MIN_ITEM_BASKETS", 1)
    monkeypatch.setattr(baskets, "MIN_PAIR_BASKETS", 1)
    lines = pd.DataFrame({
        "invoice":    ["1", "1", "2", "2", "3", "3", "4", "4"],
        "stock_code": ["A", "B", "A", "B", "A", "C", "C", "D"],
    })
    rules, n_baskets = baskets.pair_rules(lines)
    assert n_baskets == 4
    ab = rules[(rules["antecedent"] == "A") & (rules["consequent"] == "B")].iloc[0]
    assert ab["baskets"] == 2
    assert ab["support"] == pytest.approx(2 / 4)
    assert ab["confidence"] == pytest.approx(2 / 3)            # A is in 3 baskets
    assert ab["lift"] == pytest.approx((2 / 3) / (2 / 4))      # B is in 2 of 4 baskets
    # Every pair appears in both directions.
    assert len(rules) % 2 == 0


def test_recommendation_evaluation_is_out_of_time(monkeypatch):
    """Rules come only from the training period; the baseline is the training best-seller.

    Training: P and X are the best-sellers (bought together a lot); A&B and C&D are pairs.
    Test (after the cutoff): {A, B}, {C, D}, and {E, F}, a pair never seen in training.
    """
    monkeypatch.setattr(baskets, "MIN_ITEM_BASKETS", 1)
    monkeypatch.setattr(baskets, "MIN_PAIR_BASKETS", 1)
    train = [["P", "X"]] * 5 + [["A", "B"], ["C", "D"]]
    test = [["A", "B"], ["C", "D"], ["E", "F"]]
    rows = [(f"T{i}", code, pd.Timestamp("2011-01-01")) for i, b in enumerate(train) for code in b]
    rows += [(f"S{i}", code, pd.Timestamp("2011-12-01")) for i, b in enumerate(test) for code in b]
    sales = pd.DataFrame(rows, columns=["invoice", "stock_code", "date"])

    result = baskets.evaluate(sales)
    top1 = result["by_k"][0]
    assert result["cases"] == 4                  # A, B, C, D; E and F have no training rules (no leakage)
    assert result["coverage"] == pytest.approx(4 / 6)
    assert top1["rules"] == 1.0                  # A -> B, B -> A, C -> D, D -> C all appear in the order
    assert top1["popular"] == 0.0                # the best-seller P is never in the test orders
