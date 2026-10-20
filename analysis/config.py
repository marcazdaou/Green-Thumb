"""Paths and constants shared by every step of the pipeline."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Raw data (downloaded on first run, not committed: ~45 MB).
DATA_URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"
RAW_DIR = ROOT / "data" / "raw"
RAW_ZIP = RAW_DIR / "online_retail_ii.zip"
RAW_XLSX = RAW_DIR / "online_retail_II.xlsx"
RAW_CACHE = RAW_DIR / "online_retail_ii.parquet"   # fast cache of the Excel file

# Outputs read by the Django site (small JSON files, committed so the site
# works without re-running the pipeline).
RESULTS_FILE = ROOT / "backend" / "insights" / "data" / "results.json"
CATALOG_FILE = ROOT / "backend" / "store" / "data" / "catalog.json"

SEED = 42
CURRENCY = "GBP"   # the retailer's prices are in British pounds
