"""The Insights dashboard.

Two kinds of data, kept clearly separate on the page:
  1. Research results from the real UCI Online Retail II dataset
     (precomputed by the analysis pipeline, read from results.json).
  2. Live activity of this demo store (orders and reviews placed on the site),
     queried from the database on each request.
"""
from django.db.models import Avg, Count, F, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import render

from store.models import OrderItem, Order, Review

from .loader import load_results


def store_activity() -> dict:
    """Orders and reviews placed on this site, grouped by real calendar month.

    Grouping by a truncated date (not a "Mon YYYY" string) keeps months in
    time order. Orders still waiting for a Stripe payment are left out.
    """
    orders = Order.objects.exclude(status=Order.Status.PENDING)
    items = OrderItem.objects.exclude(order__status=Order.Status.PENDING)
    by_month = (orders.annotate(month=TruncMonth("created_at")).values("month")
                .annotate(orders=Count("id"), revenue=Sum("total")).order_by("month"))
    by_product = (items.values(name=F("product__name"))
                  .annotate(units=Sum("quantity"), revenue=Sum(F("quantity") * F("unit_price")))
                  .order_by("-revenue")[:10])
    reviews = Review.objects.aggregate(n=Count("id"), avg=Avg("stars"))
    return {
        "orders": orders.count(),
        "revenue": orders.aggregate(total=Sum("total"))["total"] or 0,
        "reviews": reviews["n"], "avg_stars": reviews["avg"],
        "by_month": [{"month": r["month"].strftime("%Y-%m"), "orders": r["orders"], "revenue": float(r["revenue"])}
                     for r in by_month],
        "by_product": [{"name": r["name"], "units": r["units"], "revenue": float(r["revenue"])} for r in by_product],
    }


def findings(results: dict) -> dict:
    """Headline takeaways for the dashboard, computed from the results (no hand-typed numbers)."""
    ov, seg, pred = results["overview"], results["segments"], results["prediction"]
    top_seg = max(seg["segments"], key=lambda s: s["revenue_share"])
    best = next(m for m in pred["comparison"] if m["model"] == pred["best_model"])
    baseline = next(m for m in pred["comparison"] if "baseline" in m["model"])
    cal = pred["calibration"]
    n = sum(c["n"] for c in cal)
    mean_pred = sum(c["predicted"] * c["n"] for c in cal) / n
    mean_obs = sum(c["observed"] * c["n"] for c in cal) / n
    weekly = ov["weekly_pattern"]
    totals_by_day = [sum(row) for row in weekly["orders"]]
    totals_by_hour = [sum(col) for col in zip(*weekly["orders"])]
    uk = next((c for c in ov["countries"] if c["country"] == "United Kingdom"), None)
    peak = max((m for m in ov["monthly"] if not m["partial"]), key=lambda m: m["revenue"])
    return {
        "top_segment": top_seg,
        "best": best, "baseline": baseline, "vs_baseline": pred["vs_baseline"],
        "top_decile": pred["lift"][0], "mean_predicted": mean_pred, "mean_observed": mean_obs,
        "busiest_day": weekly["days"][totals_by_day.index(max(totals_by_day))],
        "busiest_hour": weekly["hours"][totals_by_hour.index(max(totals_by_hour))],
        "saturday_orders": totals_by_day[weekly["days"].index("Sat")] if "Sat" in weekly["days"] else 0,
        "yoy_percent": 100 * ov["year_over_year"]["growth"],
        "uk_share": uk["share"] if uk else None,
        "peak_month": peak,
        "top_rule": results["baskets"]["top_rules"][0] if results["baskets"]["top_rules"] else None,
        # Out-of-time test of the recommendations at K=3 (the store shows 3 suggestions).
        "rec_eval": next((r for r in results["baskets"].get("evaluation", {}).get("by_k", []) if r["k"] == 3), None),
    }


def dashboard_view(request):
    results = load_results()
    return render(request, "insights/dashboard.html", {
        "results": results,
        "findings": findings(results) if results else None,
        "activity": store_activity(),
    })
