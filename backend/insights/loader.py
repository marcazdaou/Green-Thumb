"""Read the pipeline's results file (written by `python -m analysis.run_pipeline`).

The file is re-read only when it changes on disk, so the dashboard picks up a
re-run of the pipeline without restarting the server.
"""
import json
from pathlib import Path

RESULTS = Path(__file__).resolve().parent / "data" / "results.json"
_cache = {"mtime": None, "data": None}


def load_results() -> dict | None:
    """The results dict, or None if the pipeline has not been run."""
    if not RESULTS.exists():
        return None
    mtime = RESULTS.stat().st_mtime
    if _cache["mtime"] != mtime:
        _cache.update(mtime=mtime, data=json.loads(RESULTS.read_text(encoding="utf-8")))
    return _cache["data"]
