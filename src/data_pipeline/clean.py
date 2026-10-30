
"""Stage 2 - Clean & validate: normalise text, coerce types, drop bad rows."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

VALID_REGIONS = {"North", "South", "East", "West"}
VALID_CHANNELS = {"online", "in-store", "partner"}


@dataclass
class CleaningReport:
    """Row-level accounting of what the cleaning stage did."""

    rows_in: int = 0
    rows_out: int = 0
    duplicates_removed: int = 0
    invalid_date: int = 0
    invalid_quantity: int = 0
    invalid_price: int = 0
    missing_region_filled: int = 0
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "rows_in": self.rows_in,
            "rows_out": self.rows_out,
            "duplicates_removed": self.duplicates_removed,
            "invalid_date": self.invalid_date,
            "invalid_quantity": self.invalid_quantity,
            "invalid_price": self.invalid_price,
            "missing_region_filled": self.missing_region_filled,
        }
        
        
def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, CleaningReport]:
    """Return a cleaned, type-correct DataFrame plus a CleaningReport.

    Rules:
      * strip/normalise ``region`` and ``channel`` casing,
      * fill missing region with ``"Unknown"``,
      * parse ``order_date`` (drop unparseable),
      * coerce numeric columns and drop rows with non-positive qty/price,
      * drop exact duplicate rows.
    """
    report = CleaningReport(rows_in=len(df))
    df = df.copy()

    # Drop exact duplicates first.
    before = len(df)
    df = df.drop_duplicates()
    report.duplicates_removed = before - len(df)

    # Normalise categorical text.
    df["region"] = df["region"].str.strip().str.title()
    df["channel"] = df["channel"].str.strip().str.lower()

    # Fill missing regions.
    missing_region = df["region"].isin(["", "Nan"]) | df["region"].isna()
    report.missing_region_filled = int(missing_region.sum())
    df.loc[missing_region, "region"] = "Unknown"

    
    # Parse dates; unparseable -> NaT.
    df["order_date"] = pd.to_datetime(df["order_date"], format="%Y-%m-%d", errors="coerce")
    bad_date = df["order_date"].isna()
    report.invalid_date = int(bad_date.sum())
    df = df[~bad_date]

    # Numeric coercion.
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
    df["discount_pct"] = pd.to_numeric(df["discount_pct"], errors="coerce").fillna(0)

    bad_qty = df["quantity"].isna() | (df["quantity"] <= 0)
    report.invalid_quantity = int(bad_qty.sum())
    df = df[~bad_qty]

    bad_price = df["unit_price"].isna() | (df["unit_price"] <= 0)
    report.invalid_price = int(bad_price.sum())
    df = df[~bad_price]

    # Final type tidy.
    df["quantity"] = df["quantity"].astype(int)
    df["discount_pct"] = df["discount_pct"].astype(float)

    # Guard against unexpected categorical values (report only, keep rows).
    unknown_channels = set(df["channel"].unique()) - VALID_CHANNELS
    if unknown_channels:
        report.notes.append(f"Unexpected channels seen: {sorted(unknown_channels)}")

    df = df.reset_index(drop=True)
    report.rows_out = len(df)
    return df, report


