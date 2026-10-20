"""Cleaning rules in analysis/data.py."""
from analysis.data import clean


def test_each_cleaning_rule_removes_exactly_its_row(raw_transactions):
    sales, cancellations, funnel = clean(raw_transactions)
    assert funnel["raw_rows"] == 8
    assert funnel["after_removing_duplicates"] == 7          # duplicate line removed
    assert funnel["cancellation_rows"] == 1
    assert funnel["after_setting_aside_cancellations"] == 6
    assert funnel["after_removing_reversed_sales"] == 5       # the 80,995-unit order it cancelled
    assert funnel["after_keeping_products_only"] == 4         # POSTAGE removed
    assert funnel["clean_rows"] == 3                          # zero-price row removed
    assert funnel["rows_with_customer_id"] == 2


def test_clean_sales_have_revenue_and_no_invalid_rows(raw_transactions):
    sales, _, _ = clean(raw_transactions)
    assert (sales["quantity"] > 0).all() and (sales["price"] > 0).all()
    assert (sales["revenue"] == sales["quantity"] * sales["price"]).all()
    assert not sales["invoice"].str.startswith("C").any()
    assert sales["quantity"].max() < 80995                    # the reversed bulk order is gone


def test_funnel_never_increases(raw_transactions):
    _, _, funnel = clean(raw_transactions)
    steps = ["raw_rows", "after_removing_duplicates", "after_setting_aside_cancellations",
             "after_removing_reversed_sales", "after_keeping_products_only", "clean_rows"]
    counts = [funnel[s] for s in steps]
    assert counts == sorted(counts, reverse=True)
