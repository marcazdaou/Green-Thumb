"""Step 6: market basket analysis ("frequently bought together").

Each order (invoice) is a basket of products. For a pair of products A and B:
  support    = share of baskets containing both
  confidence = P(B in basket | A in basket)
  lift       = confidence / P(B)   (> 1 means bought together more than chance)

Only products that appear in at least MIN_ITEM_BASKETS baskets are
considered, and a rule needs at least MIN_PAIR_BASKETS baskets so that it is
not driven by a handful of orders. The co-occurrence counts are computed with
a sparse basket x product matrix (X^T X), which is exact and fast.

evaluate() checks whether the rules actually predict anything: rules learned
from orders *before* a cutoff are tested on orders *after* it (out-of-time),
against a best-seller baseline.
"""
import numpy as np
import pandas as pd
from scipy import sparse

from .catalog import pretty_name
from .config import SEED

MIN_ITEM_BASKETS = 150
MIN_PAIR_BASKETS = 60
TEST_DAYS = 90            # evaluation window: the last 90 days of data
K_VALUES = (1, 3, 5)      # the store shows 3 suggestions per product


def pair_rules(sales: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """All directed rules A -> B meeting the minimum counts."""
    lines = sales[["invoice", "stock_code"]].drop_duplicates()
    sizes = lines.groupby("invoice").size()
    lines = lines[lines["invoice"].isin(sizes[sizes >= 2].index)]          # single-item baskets carry no pairs
    n_baskets = lines["invoice"].nunique()

    item_counts = lines["stock_code"].value_counts()
    items = item_counts[item_counts >= MIN_ITEM_BASKETS].index
    lines = lines[lines["stock_code"].isin(items)]

    basket_idx = pd.factorize(lines["invoice"])[0]
    item_idx, item_codes = pd.factorize(lines["stock_code"])
    X = sparse.csr_matrix((np.ones(len(lines), dtype=np.int32), (basket_idx, item_idx)))
    co = (X.T @ X).tocoo()                                                 # co-occurrence counts

    mask = (co.row != co.col) & (co.data >= MIN_PAIR_BASKETS)
    a, b, both = co.row[mask], co.col[mask], co.data[mask]
    count = np.asarray(X.sum(axis=0)).ravel()
    rules = pd.DataFrame({
        "antecedent": item_codes[a], "consequent": item_codes[b], "baskets": both,
        "support": both / n_baskets,
        "confidence": both / count[a],
        "lift": (both / count[a]) / (count[b] / n_baskets),
    })
    return rules, n_baskets


def _basket_sets(sales: pd.DataFrame) -> list[frozenset]:
    """Distinct products per order, for orders with at least 2 products."""
    sets = sales.groupby("invoice")["stock_code"].agg(frozenset)
    return [b for b in sets if len(b) >= 2]


def _bootstrap_rate(hits: np.ndarray, cases: np.ndarray, n: int = 1000) -> tuple[float, float]:
    """95% CI for sum(hits)/sum(cases), resampling whole baskets (cases in a basket are not independent)."""
    rng = np.random.default_rng(SEED)
    rates = []
    for _ in range(n):
        i = rng.integers(0, len(hits), len(hits))
        rates.append(hits[i].sum() / cases[i].sum())
    return float(np.percentile(rates, 2.5)), float(np.percentile(rates, 97.5))


def _bootstrap_difference(hits_a: np.ndarray, hits_b: np.ndarray, cases: np.ndarray, n: int = 1000) -> tuple[float, float]:
    """Paired 95% CI for rate(a) - rate(b): both methods scored on the same resampled baskets."""
    rng = np.random.default_rng(SEED)
    diffs = []
    for _ in range(n):
        i = rng.integers(0, len(cases), len(cases))
        diffs.append((hits_a[i].sum() - hits_b[i].sum()) / cases[i].sum())
    return float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))


def evaluate(sales: pd.DataFrame) -> dict:
    """Out-of-time hit rate@K of the basket rules vs recommending best-sellers.

    Rules are learned only from orders before the cutoff. Then, for every order
    after the cutoff and every product A in it that has rules: show the top K
    products by lift for A. It is a *hit* if at least one of them is also in
    that order. The baseline shows the K best-selling products (other than A)
    from the same training period. Both are scored on exactly the same cases.
    """
    cutoff = sales["date"].max() - pd.Timedelta(days=TEST_DAYS)
    train, test = sales[sales["date"] < cutoff], sales[sales["date"] >= cutoff]
    rules, _ = pair_rules(train)

    k_max = max(K_VALUES)
    ranked = {a: grp.sort_values(["lift", "confidence"], ascending=False)["consequent"].head(k_max).tolist()
              for a, grp in rules.groupby("antecedent")}
    popular = train.groupby("stock_code")["invoice"].nunique().sort_values(ascending=False).index[:k_max + 1].tolist()

    baskets = _basket_sets(test)
    # Per basket: number of cases and hits at each K, for rules and for the baseline.
    cases = np.zeros(len(baskets))
    hits = {(m, k): np.zeros(len(baskets)) for m in ("rules", "popular") for k in K_VALUES}
    total_items = 0
    for i, basket in enumerate(baskets):
        total_items += len(basket)
        for a in basket:
            recs = ranked.get(a)
            if not recs:
                continue
            cases[i] += 1
            pop = [p for p in popular if p != a]
            for k in K_VALUES:
                hits["rules", k][i] += any(r in basket for r in recs[:k])
                hits["popular", k][i] += any(p in basket for p in pop[:k])

    keep = cases > 0
    cases = cases[keep]
    hits = {key: h[keep] for key, h in hits.items()}
    result = {"cutoff": str(cutoff.date()), "test_days": TEST_DAYS,
              "train_baskets": int(train["invoice"].nunique()), "test_baskets": int(keep.sum()),
              "cases": int(cases.sum()), "coverage": float(cases.sum() / total_items), "by_k": []}
    for k in K_VALUES:
        row = {"k": k}
        for m in ("rules", "popular"):
            row[m] = float(hits[m, k].sum() / cases.sum())
            row[f"{m}_ci"] = _bootstrap_rate(hits[m, k], cases)
        row["lift_over_popular"] = row["rules"] / row["popular"] if row["popular"] else None
        row["difference"] = row["rules"] - row["popular"]
        row["difference_ci"] = _bootstrap_difference(hits["rules", k], hits["popular", k], cases)
        result["by_k"].append(row)
    return result


def run(sales: pd.DataFrame, catalog_codes: list[str]) -> dict:
    rules, n_baskets = pair_rules(sales)
    names = sales.groupby("stock_code")["description"].agg(lambda s: pretty_name(s.dropna().mode().iat[0]))

    # Strongest rules overall: high lift AND reasonable confidence; one direction per pair.
    strong = rules[rules["confidence"] >= 0.5].sort_values("lift", ascending=False)
    strong = strong[strong["antecedent"] < strong["consequent"]].head(15)
    top = [{"if_bought": names[r.antecedent], "also_buy": names[r.consequent], "baskets": int(r.baskets),
            "support": float(r.support), "confidence": float(r.confidence), "lift": float(r.lift)}
           for r in strong.itertuples()]

    # Store recommendations: for each catalog product, the catalog products most
    # often bought with it (lift > 1.5), so every suggestion can be added to the cart.
    in_store = rules[rules["antecedent"].isin(catalog_codes) & rules["consequent"].isin(catalog_codes)
                     & (rules["lift"] > 1.5)]
    recommendations = {
        code: [{"stock_code": r.consequent, "confidence": round(float(r.confidence), 4), "lift": round(float(r.lift), 2)}
               for r in grp.sort_values("lift", ascending=False).head(3).itertuples()]
        for code, grp in in_store.groupby("antecedent")
    }
    return {
        # Co-occurrence is symmetric, so every pair appears as two rules (A -> B and B -> A).
        "n_baskets": int(n_baskets), "n_rules": int(len(rules)), "n_pairs": int(len(rules) // 2),
        "min_item_baskets": MIN_ITEM_BASKETS, "min_pair_baskets": MIN_PAIR_BASKETS,
        "top_rules": top,
        "evaluation": evaluate(sales),
    }, recommendations
