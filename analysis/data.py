"""Step 1: download, load and clean the transactions.

Cleaning rules (each step is counted so the dashboard can show the funnel):
  1. Drop exact duplicate rows (the same line exported twice).
  2. Set cancellations aside (invoice numbers starting with "C"); they are
     used for the return rate, not as sales.
  3. Drop sales that a later cancellation fully reversed (same customer,
     product and quantity). Without this, a few huge orders that were placed
     and immediately cancelled (e.g. 80,995 units of one item) dominate
     revenue.
  4. Keep real products only: stock codes are 5 digits plus an optional
     letter suffix; postage, bank charges, manual adjustments, Amazon fees
     and gift vouchers are removed.
  5. Keep rows with a positive quantity and a positive price.
"""
import zipfile
from urllib.request import urlretrieve

import pandas as pd

from .config import DATA_URL, RAW_CACHE, RAW_DIR, RAW_XLSX, RAW_ZIP

PRODUCT_CODE = r"^\d{5}[A-Za-z]{0,2}$"
COLUMNS = {"Invoice": "invoice", "StockCode": "stock_code", "Description": "description",
           "Quantity": "quantity", "InvoiceDate": "date", "Price": "price",
           "Customer ID": "customer_id", "Country": "country"}


def load_raw() -> pd.DataFrame:
    """Raw transactions, downloading the dataset on first use.

    Reading the Excel file takes ~3 minutes, so a Parquet copy is cached.
    """
    if RAW_CACHE.exists():
        return pd.read_parquet(RAW_CACHE)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if not RAW_XLSX.exists():
        if not RAW_ZIP.exists():
            print(f"Downloading {DATA_URL} ...", flush=True)
            urlretrieve(DATA_URL, RAW_ZIP)
        with zipfile.ZipFile(RAW_ZIP) as z:
            z.extractall(RAW_DIR)
    print("Reading the Excel file (one time, ~3 minutes) ...", flush=True)
    sheets = pd.read_excel(RAW_XLSX, sheet_name=None,
                           dtype={"Invoice": str, "StockCode": str, "Description": str, "Country": str})
    raw = pd.concat(sheets.values(), ignore_index=True)
    raw.to_parquet(RAW_CACHE, index=False)
    return raw


def clean(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Apply the cleaning rules.

    Returns (sales, cancellations, funnel) where `funnel` records how many
    rows each rule removed.
    """
    df = raw.rename(columns=COLUMNS).copy()
    df["stock_code"] = df["stock_code"].astype(str).str.strip().str.upper()
    df["description"] = df["description"].astype("string").str.strip()
    funnel = {"raw_rows": len(df)}

    df = df.drop_duplicates()
    funnel["after_removing_duplicates"] = len(df)

    is_cancel = df["invoice"].str.startswith("C")
    cancellations = df[is_cancel].copy()
    sales = df[~is_cancel].copy()
    funnel["cancellation_rows"] = len(cancellations)
    funnel["after_setting_aside_cancellations"] = len(sales)

    sales = drop_reversed_sales(sales, cancellations)
    funnel["after_removing_reversed_sales"] = len(sales)

    sales = sales[sales["stock_code"].str.match(PRODUCT_CODE)]
    funnel["after_keeping_products_only"] = len(sales)

    sales = sales[(sales["quantity"] > 0) & (sales["price"] > 0)].copy()
    funnel["clean_rows"] = len(sales)

    sales["revenue"] = sales["quantity"] * sales["price"]
    sales["customer_id"] = sales["customer_id"].astype("Int64")
    funnel["rows_with_customer_id"] = int(sales["customer_id"].notna().sum())
    return sales.reset_index(drop=True), cancellations.reset_index(drop=True), funnel


def drop_reversed_sales(sales: pd.DataFrame, cancellations: pd.DataFrame) -> pd.DataFrame:
    """Remove sale lines exactly reversed by a cancellation.

    A sale is "reversed" when a cancellation exists for the same customer,
    product and absolute quantity, dated at or after the sale. Each
    cancellation removes at most one sale (the latest earlier one).
    """
    cancels = cancellations.dropna(subset=["customer_id"]).copy()
    cancels["quantity"] = -cancels["quantity"]
    key = ["customer_id", "stock_code", "quantity"]

    candidates = sales.dropna(subset=["customer_id"]).reset_index()  # keep original index
    matched = candidates.merge(cancels[key + ["date"]].rename(columns={"date": "cancel_date"}), on=key)
    matched = matched[matched["date"] <= matched["cancel_date"]]
    # One sale per cancellation: the most recent sale before it.
    matched = matched.sort_values("date").groupby(key + ["cancel_date"]).tail(1)
    return sales.drop(index=matched["index"].unique())
