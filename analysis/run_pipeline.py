"""Run every step and write the files the website reads.

    python -m analysis.run_pipeline        (from the repository root, ~1-2 minutes;
                                             the first run also downloads ~45 MB)

Outputs:
    backend/insights/data/results.json   everything the Insights dashboard shows
    backend/store/data/catalog.json      the store's products + recommendations
"""
import json
import time
import warnings

from . import baskets, catalog, metrics, repurchase, segmentation
from .config import CATALOG_FILE, CURRENCY, DATA_URL, RESULTS_FILE
from .data import clean, load_raw

DATASET = {
    "name": "Online Retail II",
    "publisher": "UCI Machine Learning Repository",
    "citation": "Chen, D. (2012). Online Retail II [Dataset]. UCI Machine Learning Repository. "
                "https://doi.org/10.24432/C5CG6D",
    "license": "CC BY 4.0",
    "url": DATA_URL,
    "description": "All transactions of a UK-based, registered non-store online retailer that mainly sells "
                   "unique all-occasion giftware; many of its customers are wholesalers.",
}


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1, default=str), encoding="utf-8")
    print(f"  wrote {path.relative_to(path.parents[2])} ({path.stat().st_size / 1e3:.0f} KB)")


def main():
    warnings.filterwarnings("ignore", category=UserWarning)
    started = time.time()

    def step(label):
        print(f"[{time.time() - started:5.1f}s] {label}", flush=True)

    step("Loading and cleaning transactions")
    sales, cancellations, funnel = clean(load_raw())

    step("Business metrics and cohort retention")
    monthly_rows = metrics.monthly(sales)
    overview = {
        "kpis": metrics.kpis(sales, cancellations),
        "monthly": monthly_rows,
        "year_over_year": metrics.year_over_year(monthly_rows),
        "countries": metrics.countries(sales),
        "weekly_pattern": metrics.weekly_pattern(sales),
        "top_products": metrics.top_products(sales),
    }
    cohorts = metrics.cohort_retention(sales)

    step("Customer segmentation (RFM + k-means)")
    segments = segmentation.segment(sales)

    step("Repurchase prediction (out-of-time validation)")
    prediction = repurchase.run(sales, cancellations)

    step("Store catalog and market basket analysis")
    products = catalog.build_catalog(sales)
    basket_results, recommendations = baskets.run(sales, products["stock_code"].tolist())

    write_json(RESULTS_FILE, {
        "dataset": DATASET, "currency": CURRENCY, "funnel": funnel,
        "overview": overview, "cohorts": cohorts, "segments": segments,
        "prediction": prediction, "baskets": basket_results,
    })
    write_json(CATALOG_FILE, {
        "dataset": DATASET["citation"], "currency": CURRENCY,
        "products": [{
            "stock_code": r.stock_code, "name": r.display_name, "category": r.category, "image": r.image,
            "price": float(r.price), "customers": int(r.customers), "orders": int(r.orders),
            "units_sold": int(r.units), "recommendations": recommendations.get(r.stock_code, []),
        } for r in products.itertuples()],
    })
    step("Done")


if __name__ == "__main__":
    main()
