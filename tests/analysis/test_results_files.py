"""Consistency checks on the committed pipeline outputs that the website reads."""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def results():
    return json.loads((ROOT / "backend/insights/data/results.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def catalog():
    return json.loads((ROOT / "backend/store/data/catalog.json").read_text(encoding="utf-8"))


def test_confidence_intervals_contain_their_estimates(results):
    for m in results["prediction"]["comparison"]:
        assert m["auc_ci_low"] <= m["roc_auc"] <= m["auc_ci_high"]
    d = results["prediction"]["vs_baseline"]
    assert d["ci_low"] <= d["difference"] <= d["ci_high"]


def test_model_beats_random_and_baseline(results):
    best = max(results["prediction"]["comparison"], key=lambda m: m["roc_auc"])
    assert best["roc_auc"] > 0.7
    assert results["prediction"]["vs_baseline"]["ci_low"] > 0


def test_segments_cover_every_customer(results):
    seg = results["segments"]
    assert sum(s["customers"] for s in seg["segments"]) == seg["n_customers"]
    assert sum(s["revenue_share"] for s in seg["segments"]) == pytest.approx(1, abs=1e-3)


def test_monthly_series_is_chronological(results):
    months = [m["month"] for m in results["overview"]["monthly"]]
    assert months == sorted(months)


def test_catalog_recommendations_point_to_catalog_products(catalog):
    codes = {p["stock_code"] for p in catalog["products"]}
    assert len(codes) == len(catalog["products"])               # no duplicate products
    for p in catalog["products"]:
        assert p["price"] > 0
        for r in p["recommendations"]:
            assert r["stock_code"] in codes and r["stock_code"] != p["stock_code"]
            assert r["lift"] > 1


def test_recommendations_beat_best_sellers_out_of_time(results):
    """The paired CI for (rules - best-sellers) excludes zero at every K."""
    evaluation = results["baskets"]["evaluation"]
    assert evaluation["test_baskets"] > 1000
    for row in evaluation["by_k"]:
        assert row["difference_ci"][0] > 0
        assert row["rules_ci"][0] <= row["rules"] <= row["rules_ci"][1]
