"""Shared test fixtures.

`raw_transactions` is a tiny hand-made table in the same format as the real
dataset, designed so every cleaning rule has exactly one row to act on. It is
test input only; the project's results use the real data.
"""
import pandas as pd
import pytest


def tx(invoice, code, qty, price, customer, date, desc="ITEM", country="United Kingdom"):
    return {"Invoice": invoice, "StockCode": code, "Description": desc, "Quantity": qty,
            "InvoiceDate": pd.Timestamp(date), "Price": price, "Customer ID": customer, "Country": country}


@pytest.fixture
def raw_transactions():
    rows = [
        tx("1001", "85099B", 10, 2.0, 1.0, "2011-01-03 10:00", "JUMBO BAG RED RETROSPOT"),  # normal sale
        tx("1001", "85099B", 10, 2.0, 1.0, "2011-01-03 10:00", "JUMBO BAG RED RETROSPOT"),  # exact duplicate
        tx("1002", "20725", 5, 1.65, 2.0, "2011-01-04 11:00", "LUNCH BAG RED RETROSPOT"),   # normal sale
        tx("1003", "22487", 80995, 2.08, 3.0, "2011-02-01 09:00", "PLANT LADDER"),          # reversed below
        tx("C1004", "22487", -80995, 2.08, 3.0, "2011-02-01 09:05", "PLANT LADDER"),        # its cancellation
        tx("1005", "POST", 1, 18.0, 1.0, "2011-02-02 12:00", "POSTAGE"),                     # not a product
        tx("1006", "20725", 3, 0.0, 2.0, "2011-02-03 12:00", "LUNCH BAG RED RETROSPOT"),    # zero price
        tx("1007", "20725", 2, 1.65, None, "2011-02-04 12:00", "LUNCH BAG RED RETROSPOT"),  # no customer id
    ]
    return pd.DataFrame(rows)
