"""Step 4: customer segmentation (RFM + k-means).

Each identified customer is described by:
  Recency   - days since their last order (measured from the day after the data ends)
  Frequency - number of orders
  Monetary  - total spend

The three values are heavily skewed, so they are log-transformed and
standardized before k-means. The number of clusters is chosen by silhouette
score among k = 3..6 (fewer than 3 is too coarse to act on; more than 6 is
hard to describe). Segment names are derived from each cluster's medians
relative to the overall medians, so they always match the data.
"""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from .config import SEED

K_RANGE = range(2, 9)          # silhouette is reported for all of these...
K_CHOICES = range(3, 7)        # ...and the best of these is used


def rfm_table(sales: pd.DataFrame) -> pd.DataFrame:
    known = sales.dropna(subset=["customer_id"])
    snapshot = known["date"].max().normalize() + pd.Timedelta(days=1)
    return known.groupby("customer_id").agg(
        recency=("date", lambda d: (snapshot - d.max()).days),
        frequency=("invoice", "nunique"),
        monetary=("revenue", "sum"),
    )


def segment(sales: pd.DataFrame) -> dict:
    rfm = rfm_table(sales)
    X = StandardScaler().fit_transform(np.log1p(rfm[["recency", "frequency", "monetary"]]))

    rng = np.random.default_rng(SEED)
    sample = rng.choice(len(X), size=min(4000, len(X)), replace=False)  # silhouette is O(n^2)
    scores = {}
    for k in K_RANGE:
        labels = KMeans(n_clusters=k, n_init=10, random_state=SEED).fit_predict(X)
        scores[k] = float(silhouette_score(X[sample], labels[sample]))
    best_k = max(K_CHOICES, key=lambda k: scores[k])

    rfm["cluster"] = KMeans(n_clusters=best_k, n_init=10, random_state=SEED).fit_predict(X)
    rfm["segment"] = name_segments(rfm)

    total_rev = rfm["monetary"].sum()
    summary = (rfm.groupby("segment").agg(
        customers=("monetary", "size"), revenue=("monetary", "sum"),
        recency=("recency", "median"), frequency=("frequency", "median"), monetary=("monetary", "median"))
        .sort_values("revenue", ascending=False).reset_index())
    summary["customer_share"] = summary["customers"] / len(rfm)
    summary["revenue_share"] = summary["revenue"] / total_rev

    points = rfm.sample(n=min(2500, len(rfm)), random_state=SEED)
    return {
        "k": best_k,
        "silhouette": {str(k): round(v, 4) for k, v in scores.items()},
        "segments": summary.round(4).to_dict(orient="records"),
        "points": {"recency": points["recency"].tolist(), "frequency": points["frequency"].tolist(),
                   "monetary": points["monetary"].round(2).tolist(), "segment": points["segment"].tolist()},
        "n_customers": int(len(rfm)),
    }


def name_segments(rfm: pd.DataFrame) -> pd.Series:
    """Readable names from each cluster's median recency, frequency and spend.

    Recent = median recency below the overall median; frequent = median order
    count above the overall median. The cluster with the highest median spend
    that is also recent and frequent is called "Champions".
    """
    med = rfm[["recency", "frequency", "monetary"]].median()
    prof = rfm.groupby("cluster")[["recency", "frequency", "monetary"]].median()
    names = {}
    for c, p in prof.iterrows():
        recent, frequent = p["recency"] < med["recency"], p["frequency"] > med["frequency"]
        names[c] = {(True, True): "Loyal regulars", (True, False): "New or occasional",
                    (False, True): "At risk", (False, False): "Lapsed one-timers"}[(recent, frequent)]
    loyal = [c for c in prof.index if names[c] == "Loyal regulars"]
    if loyal:
        names[prof.loc[loyal, "monetary"].idxmax()] = "Champions"
    # If two clusters still share a name, number them by spend so labels stay unique.
    for name in set(names.values()):
        same = [c for c in names if names[c] == name]
        if len(same) > 1:
            for i, c in enumerate(prof.loc[same, "monetary"].sort_values(ascending=False).index, 1):
                names[c] = f"{name} ({'higher' if i == 1 else 'lower'} spend)" if len(same) == 2 else f"{name} {i}"
    return rfm["cluster"].map(names)
