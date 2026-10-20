"""Step 5: predict which customers will buy again in the next 90 days.

Why it matters: a retailer can target win-back offers at customers who are
unlikely to return, and avoid discounting customers who would return anyway.

Design (out-of-time validation, no leakage):
  * A "snapshot" at date T describes each customer using only orders before T,
    and the label is whether they order in [T, T + 90 days).
  * Training uses several snapshots whose label windows all end before the
    test snapshot begins. The test snapshot is 90 days before the data ends,
    so the model is always evaluated on the future relative to its training.
  * Models: a one-feature recency rule (baseline), logistic regression and
    gradient boosting. ROC AUC on the test snapshot gets a 95% bootstrap CI.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score, roc_curve
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

from .config import SEED

HORIZON_DAYS = 90
TRAIN_SNAPSHOTS = ["2010-09-10", "2010-12-10", "2011-03-10", "2011-06-10"]
TEST_SNAPSHOT = "2011-09-10"
FEATURES = ["recency_days", "frequency", "monetary", "tenure_days", "avg_order_value", "distinct_products",
            "orders_last_90d", "revenue_last_90d", "days_between_orders", "return_rate", "is_uk"]
FEATURE_LABELS = {
    "recency_days": "Days since last order", "frequency": "Number of orders", "monetary": "Total spend",
    "tenure_days": "Days since first order", "avg_order_value": "Average order value",
    "distinct_products": "Distinct products bought", "orders_last_90d": "Orders in last 90 days",
    "revenue_last_90d": "Spend in last 90 days", "days_between_orders": "Average days between orders",
    "return_rate": "Share of value returned", "is_uk": "UK customer",
}


def snapshot(sales: pd.DataFrame, cancellations: pd.DataFrame, cutoff: str) -> pd.DataFrame:
    """Features from orders strictly before `cutoff`; label from the next 90 days."""
    t = pd.Timestamp(cutoff)
    known = sales.dropna(subset=["customer_id"])
    past = known[known["date"] < t]
    future = known[(known["date"] >= t) & (known["date"] < t + pd.Timedelta(days=HORIZON_DAYS))]
    recent = past[past["date"] >= t - pd.Timedelta(days=90)]

    orders = past.groupby(["customer_id", "invoice"]).agg(date=("date", "min"), value=("revenue", "sum"))
    g = orders.groupby("customer_id")
    f = pd.DataFrame({
        "recency_days": (t - g["date"].max()).dt.days,
        "frequency": g.size(),
        "monetary": g["value"].sum(),
        "tenure_days": (t - g["date"].min()).dt.days,
        "avg_order_value": g["value"].mean(),
        "distinct_products": past.groupby("customer_id")["stock_code"].nunique(),
        "orders_last_90d": recent.groupby("customer_id")["invoice"].nunique(),
        "revenue_last_90d": recent.groupby("customer_id")["revenue"].sum(),
        "is_uk": past.groupby("customer_id")["country"].agg(lambda c: float((c == "United Kingdom").mean() > 0.5)),
    }).fillna({"orders_last_90d": 0, "revenue_last_90d": 0})
    f["days_between_orders"] = f["tenure_days"] / f["frequency"]

    canc = cancellations.dropna(subset=["customer_id"])
    canc = canc[canc["date"] < t]
    returned = (-canc["quantity"] * canc["price"]).groupby(canc["customer_id"].astype("Int64")).sum()
    f["return_rate"] = (returned.reindex(f.index).fillna(0) / (f["monetary"] + returned.reindex(f.index).fillna(0)))
    f["label"] = f.index.isin(future["customer_id"].unique()).astype(int)
    f["snapshot"] = cutoff
    return f


def bootstrap_auc(y: np.ndarray, p: np.ndarray, n: int = 1000) -> tuple[float, float]:
    """95% percentile interval for ROC AUC, resampling customers."""
    rng = np.random.default_rng(SEED)
    aucs = []
    for _ in range(n):
        i = rng.integers(0, len(y), len(y))
        if y[i].min() != y[i].max():
            aucs.append(roc_auc_score(y[i], p[i]))
    return float(np.percentile(aucs, 2.5)), float(np.percentile(aucs, 97.5))


def bootstrap_auc_difference(y: np.ndarray, p_model: np.ndarray, p_base: np.ndarray, n: int = 1000) -> dict:
    """Paired bootstrap of AUC(model) - AUC(baseline) on the same resampled customers.

    Comparing two separate intervals is not a valid test; resampling the same
    customers for both models and looking at the difference is.
    """
    rng = np.random.default_rng(SEED)
    diffs = []
    for _ in range(n):
        i = rng.integers(0, len(y), len(y))
        if y[i].min() != y[i].max():
            diffs.append(roc_auc_score(y[i], p_model[i]) - roc_auc_score(y[i], p_base[i]))
    diffs = np.array(diffs)
    return {"difference": float(roc_auc_score(y, p_model) - roc_auc_score(y, p_base)),
            "ci_low": float(np.percentile(diffs, 2.5)), "ci_high": float(np.percentile(diffs, 97.5)),
            "share_of_resamples_model_better": float((diffs > 0).mean())}


def models() -> dict:
    log_scale = FunctionTransformer(np.log1p)   # all features are non-negative and skewed
    return {
        "Logistic regression": make_pipeline(log_scale, StandardScaler(), LogisticRegression(max_iter=1000)),
        "Gradient boosting": HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=15,
                                                            l2_regularization=1.0, random_state=SEED),
    }


def lift_curve(y: np.ndarray, p: np.ndarray, bins: int = 10) -> list[dict]:
    """Repurchase rate by predicted-probability decile (decile 1 = most likely)."""
    order = np.argsort(-p)
    rows = []
    for d, idx in enumerate(np.array_split(order, bins), 1):
        rows.append({"decile": d, "rate": float(y[idx].mean()), "lift": float(y[idx].mean() / y.mean())})
    return rows


def calibration(y: np.ndarray, p: np.ndarray, bins: int = 10) -> list[dict]:
    edges = np.quantile(p, np.linspace(0, 1, bins + 1))
    which = np.clip(np.searchsorted(edges, p, side="right") - 1, 0, bins - 1)
    return [{"predicted": float(p[which == b].mean()), "observed": float(y[which == b].mean()),
             "n": int((which == b).sum())} for b in range(bins) if (which == b).any()]


def run(sales: pd.DataFrame, cancellations: pd.DataFrame) -> dict:
    train = pd.concat([snapshot(sales, cancellations, c) for c in TRAIN_SNAPSHOTS])
    test = snapshot(sales, cancellations, TEST_SNAPSHOT)
    # Guard against leakage: every training label window ends before the test snapshot.
    assert pd.Timestamp(TRAIN_SNAPSHOTS[-1]) + pd.Timedelta(days=HORIZON_DAYS) <= pd.Timestamp(TEST_SNAPSHOT)

    X_tr, y_tr = train[FEATURES].to_numpy(float), train["label"].to_numpy()
    X_te, y_te = test[FEATURES].to_numpy(float), test["label"].to_numpy()

    results, predictions = {}, {}
    # Baseline: the more recently a customer ordered, the more likely they return.
    base = -test["recency_days"].to_numpy(float)
    predictions["Recency rule (baseline)"] = base
    for name, model in models().items():
        model.fit(X_tr, y_tr)
        predictions[name] = model.predict_proba(X_te)[:, 1]
        results[name] = model

    comparison = []
    for name, p in predictions.items():
        lo, hi = bootstrap_auc(y_te, p)
        row = {"model": name, "roc_auc": float(roc_auc_score(y_te, p)), "auc_ci_low": lo, "auc_ci_high": hi,
               "pr_auc": float(average_precision_score(y_te, p)),
               "top_decile_lift": lift_curve(y_te, p)[0]["lift"]}
        if name in results:
            row["brier"] = float(brier_score_loss(y_te, p))
        comparison.append(row)

    best = max((r for r in comparison if r["model"] in results), key=lambda r: r["roc_auc"])["model"]
    p_best = predictions[best]
    fpr, tpr, _ = roc_curve(y_te, p_best)
    keep = np.linspace(0, len(fpr) - 1, min(200, len(fpr))).astype(int)   # thin the curve for the browser
    fpr_b, tpr_b, _ = roc_curve(y_te, base)
    keep_b = np.linspace(0, len(fpr_b) - 1, min(200, len(fpr_b))).astype(int)

    imp = permutation_importance(results[best], X_te, y_te, scoring="roc_auc", n_repeats=5, random_state=SEED)
    importance = sorted(({"feature": FEATURE_LABELS[f], "drop_in_auc": float(m)}
                         for f, m in zip(FEATURES, imp.importances_mean)), key=lambda r: -r["drop_in_auc"])

    return {
        "horizon_days": HORIZON_DAYS, "train_snapshots": TRAIN_SNAPSHOTS, "test_snapshot": TEST_SNAPSHOT,
        "n_train": int(len(train)), "n_test": int(len(test)),
        "base_rate_train": float(y_tr.mean()), "base_rate_test": float(y_te.mean()),
        "comparison": comparison, "best_model": best,
        "vs_baseline": bootstrap_auc_difference(y_te, p_best, base),
        "roc": {"fpr": fpr[keep].round(4).tolist(), "tpr": tpr[keep].round(4).tolist(),
                "baseline_fpr": fpr_b[keep_b].round(4).tolist(), "baseline_tpr": tpr_b[keep_b].round(4).tolist()},
        "lift": lift_curve(y_te, p_best), "calibration": calibration(y_te, p_best),
        "importance": importance,
    }
