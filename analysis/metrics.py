"""Step 3: business metrics and cohort retention.

All figures use cleaned sales. Customer-level figures (customers, cohorts)
use only rows with a customer ID (~77% of rows); revenue and order figures
use every cleaned row.
"""
import numpy as np
import pandas as pd


def kpis(sales: pd.DataFrame, cancellations: pd.DataFrame) -> dict:
    """Headline numbers for the whole period."""
    orders = sales.groupby("invoice")["revenue"].sum()
    cancelled_value = float((-cancellations["quantity"] * cancellations["price"]).clip(lower=0).sum())
    return {
        "revenue": float(sales["revenue"].sum()),
        "orders": int(sales["invoice"].nunique()),
        "customers": int(sales["customer_id"].nunique()),
        "products": int(sales["stock_code"].nunique()),
        "countries": int(sales["country"].nunique()),
        "avg_order_value": float(orders.mean()),
        "median_order_value": float(orders.median()),
        # Share of gross sales value that was later cancelled or returned.
        "return_rate": cancelled_value / (float(sales["revenue"].sum()) + cancelled_value),
        "start": str(sales["date"].min().date()),
        "end": str(sales["date"].max().date()),
    }


def monthly(sales: pd.DataFrame) -> list[dict]:
    """Revenue, orders, customers and average order value per calendar month.

    Months are real dates, so they always sort in time order. The last month
    is flagged when the data stops part-way through it.
    """
    month = sales["date"].dt.to_period("M")
    by_month = sales.groupby(month).agg(revenue=("revenue", "sum"), orders=("invoice", "nunique"),
                                        customers=("customer_id", "nunique"))
    by_month["avg_order_value"] = by_month["revenue"] / by_month["orders"]
    last_day = sales["date"].max()
    rows = []
    for period, r in by_month.sort_index().iterrows():
        rows.append({"month": str(period), "revenue": round(float(r["revenue"]), 2), "orders": int(r["orders"]),
                     "customers": int(r["customers"]), "avg_order_value": round(float(r["avg_order_value"]), 2),
                     "partial": bool(period == last_day.to_period("M") and last_day.day < period.days_in_month)})
    return rows


def year_over_year(monthly_rows: list[dict]) -> dict:
    """Revenue growth of 2011 vs 2010 over the months both years fully cover (Jan-Nov)."""
    df = pd.DataFrame(monthly_rows)
    df["year"], df["m"] = df["month"].str[:4], df["month"].str[5:].astype(int)
    full = df[~df["partial"] & df["m"].between(1, 11)]
    y2010 = full.loc[full["year"] == "2010", "revenue"].sum()
    y2011 = full.loc[full["year"] == "2011", "revenue"].sum()
    return {"months": "Jan-Nov", "revenue_2010": float(y2010), "revenue_2011": float(y2011),
            "growth": float(y2011 / y2010 - 1)}


def countries(sales: pd.DataFrame, top: int = 10) -> list[dict]:
    """Revenue share of the top countries, the rest grouped as 'Other'."""
    rev = sales.groupby("country")["revenue"].sum().sort_values(ascending=False)
    cust = sales.groupby("country")["customer_id"].nunique()
    rows = [{"country": c, "revenue": float(v), "share": float(v / rev.sum()), "customers": int(cust[c])}
            for c, v in rev.head(top).items()]
    rest = rev.iloc[top:]
    rows.append({"country": "Other", "revenue": float(rest.sum()), "share": float(rest.sum() / rev.sum()),
                 "customers": int(cust[rest.index].sum())})
    return rows


def weekly_pattern(sales: pd.DataFrame) -> dict:
    """Number of orders by weekday and hour of day (when do customers order?)."""
    orders = sales.drop_duplicates("invoice")
    table = (orders.groupby([orders["date"].dt.dayofweek, orders["date"].dt.hour]).size()
             .unstack(fill_value=0))
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    return {"days": [days[d] for d in table.index], "hours": [int(h) for h in table.columns],
            "orders": table.to_numpy().tolist()}


def top_products(sales: pd.DataFrame, n: int = 15) -> list[dict]:
    from .catalog import pretty_name
    by = sales.groupby("stock_code").agg(name=("description", lambda s: s.dropna().mode().iat[0]),
                                         revenue=("revenue", "sum"), customers=("customer_id", "nunique"))
    by = by.sort_values("revenue", ascending=False).head(n)
    return [{"name": pretty_name(r["name"]), "revenue": float(r["revenue"]), "customers": int(r["customers"])}
            for _, r in by.iterrows()]


def cohort_retention(sales: pd.DataFrame, max_months: int = 12) -> dict:
    """Share of each monthly acquisition cohort that buys again k months later.

    A customer's cohort is the month of their first purchase. Cell (c, k) is
    the % of cohort c that placed an order in month c + k.
    """
    known = sales.dropna(subset=["customer_id"])
    # Stop at the last *full* month: the data ends on 9 Dec 2011, and a partial
    # month would make retention in that month look artificially low.
    last_day = known["date"].max()
    last_full = last_day.to_period("M") - (0 if last_day.is_month_end else 1)
    known = known[known["date"].dt.to_period("M") <= last_full]
    month = known["date"].dt.to_period("M")
    first = month.groupby(known["customer_id"]).transform("min")
    offset = (month - first).apply(lambda d: d.n)
    active = (pd.DataFrame({"cohort": first, "offset": offset, "customer": known["customer_id"]})
              .drop_duplicates().groupby(["cohort", "offset"])["customer"].nunique().unstack(fill_value=0))
    # Every offset gets a column, even one where no cohort had a returning customer.
    active = active.reindex(columns=range(0, int(active.columns.max()) + 1), fill_value=0)
    size = active[0]
    rate = active.div(size, axis=0)
    # The first month in the data mixes new and long-standing customers, so it is
    # not a real acquisition cohort; drop it. Keep cohorts with at least 3 months
    # of follow-up.
    rate, size = rate.iloc[1:], size.iloc[1:]
    last = month.max()
    keep = [c for c in rate.index if (last - c).n >= 3]
    rate, size = rate.loc[keep], size.loc[keep]
    cols = [k for k in range(0, max_months + 1) if k in rate.columns]
    grid = []
    for c in rate.index:
        follow = (last - c).n
        # Months not yet observable for this cohort are left empty (None), not 0%.
        grid.append([round(float(rate.loc[c, k]), 4) if k <= follow and k > 0 else (1.0 if k == 0 else None)
                     for k in cols])
    month1 = rate[1] if 1 in rate.columns else pd.Series(dtype=float)
    return {"cohorts": [str(c) for c in rate.index], "sizes": [int(s) for s in size],
            "offsets": cols, "retention": grid,
            "avg_month1": float(np.average(month1, weights=size)) if len(month1) else None,
            "avg_month3": float(np.average(rate[3], weights=size)) if 3 in rate.columns else None}
