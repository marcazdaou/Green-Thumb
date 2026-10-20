"""Business metrics, cohorts, segmentation naming and the repurchase snapshot."""
import numpy as np
import pandas as pd
import pytest

from analysis import metrics, repurchase, segmentation


def sales_frame(rows):
    df = pd.DataFrame(rows, columns=["invoice", "customer_id", "date", "revenue"])
    df["date"] = pd.to_datetime(df["date"])
    df["customer_id"] = df["customer_id"].astype("Int64")
    df["stock_code"], df["quantity"], df["price"], df["country"] = "85099B", 1, df["revenue"], "United Kingdom"
    return df


def test_monthly_is_in_time_order_and_flags_partial_month():
    sales = sales_frame([("1", 1, "2011-12-05", 10), ("2", 1, "2011-02-10", 10),
                         ("3", 2, "2010-12-10", 10), ("4", 2, "2011-11-30", 10)])
    rows = metrics.monthly(sales)
    assert [r["month"] for r in rows] == ["2010-12", "2011-02", "2011-11", "2011-12"]   # not alphabetical
    assert [r["partial"] for r in rows] == [False, False, False, True]                  # data ends 5 Dec


def test_cohort_retention_counts_returning_customers():
    # Cohort Jan: customers 1 and 2. Customer 1 returns in Feb, nobody in Mar.
    rows = [("1", 1, "2011-01-05", 5), ("2", 2, "2011-01-06", 5), ("3", 1, "2011-02-07", 5),
            ("4", 3, "2010-12-01", 5),                          # earliest month (dropped: not a real cohort)
            ("5", 3, "2011-05-31", 5)]                          # data ends on a month end
    result = metrics.cohort_retention(sales_frame(rows))
    jan = result["cohorts"].index("2011-01")
    assert result["sizes"][jan] == 2
    assert result["retention"][jan][1] == pytest.approx(0.5)   # +1 month: 1 of 2
    assert result["retention"][jan][2] == pytest.approx(0.0)   # +2 months: none


def test_segment_names_follow_the_medians():
    rfm = pd.DataFrame({
        "recency":   [5, 6, 300, 310, 10, 12, 400, 420],
        "frequency": [20, 22, 15, 14, 1, 2, 1, 1],
        "monetary":  [9000, 9500, 3000, 2800, 100, 150, 50, 60],
        "cluster":   [0, 0, 1, 1, 2, 2, 3, 3],
    })
    names = segmentation.name_segments(rfm).groupby(rfm["cluster"]).first().to_dict()
    assert names == {0: "Champions", 1: "At risk", 2: "New or occasional", 3: "Lapsed one-timers"}


def test_repurchase_snapshot_uses_only_the_past_for_features():
    sales = sales_frame([("1", 1, "2011-01-10", 100), ("2", 1, "2011-03-01", 50),
                         ("3", 2, "2011-01-20", 30),
                         ("4", 1, "2011-06-01", 999)])          # after the cutoff: must not leak into features
    cancellations = sales.iloc[0:0]
    snap = repurchase.snapshot(sales, cancellations, "2011-04-01")
    c1 = snap.loc[1]
    assert c1["frequency"] == 2 and c1["monetary"] == 150      # the June order is excluded
    assert c1["recency_days"] == (pd.Timestamp("2011-04-01") - pd.Timestamp("2011-03-01")).days
    assert snap.loc[1, "label"] == 1                           # ordered within 90 days of the cutoff
    assert snap.loc[2, "label"] == 0


def test_training_windows_end_before_test_snapshot():
    last_train_label_end = pd.Timestamp(repurchase.TRAIN_SNAPSHOTS[-1]) + pd.Timedelta(days=repurchase.HORIZON_DAYS)
    assert last_train_label_end <= pd.Timestamp(repurchase.TEST_SNAPSHOT)


def test_paired_bootstrap_detects_a_better_model():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 2000)
    good = y + rng.normal(0, 0.6, 2000)        # informative scores
    weak = y + rng.normal(0, 3.0, 2000)        # much noisier scores
    result = repurchase.bootstrap_auc_difference(y, good, weak, n=200)
    assert result["ci_low"] > 0
