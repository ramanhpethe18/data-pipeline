
"""Stage 1 - Ingest: read the raw CSV into a DataFrame."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

RAW_COLUMNS = [
    "order_id", "order_date", "region", "channel", "category",
    "product", "quantity", "unit_price", "discount_pct",
]


def ingest(csv_path: str | Path) -> pd.DataFrame:
    """Load the raw CSV, keeping every value as text for validation later.

    Reading everything as ``str`` (dtype=str) avoids pandas silently coercing
    bad values to NaN before we get a chance to report on them.
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {csv_path}")

    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)

    missing = set(RAW_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Input CSV missing required columns: {sorted(missing)}")

    return df
