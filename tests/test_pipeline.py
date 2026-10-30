
"""Tests for the clean, transform, and load stages."""
from __future__ import annotations

import sqlite3

import pandas as pd
import pytest

from data_pipeline.clean import clean
from data_pipeline.load import FACT_TABLE, load_to_sqlite, query
from data_pipeline.transform import (
    monthly_revenue,
    revenue_by_category,
    transform,
)

@pytest.fixture
def raw_df() -> pd.DataFrame:
    """A tiny raw frame mirroring the messy CSV shape (all-string columns)."""
    rows = [
        # clean baseline row
        ["ORD-1", "2023-01-05", " north ", "ONLINE", "Books", "Novel", "2", "10.00", "0"],
        # missing region -> should become "Unknown"
        ["ORD-2", "2023-01-06", "", "in-store", "Home", "Lamp", "1", "35.00", "10"],
        # bad date -> dropped
        ["ORD-3", "2023-13-40", "West", "online", "Home", "Lamp", "1", "35.00", "0"],
        # negative quantity -> dropped
        ["ORD-4", "2023-02-01", "East", "online", "Sports", "Dumbbell", "-3", "40.00", "0"],
        # missing price -> dropped
        ["ORD-5", "2023-02-02", "South", "partner", "Books", "Comic", "2", "", "0"],
        # good row for aggregation
        ["ORD-6", "2023-02-03", "North", "online", "Books", "Novel", "3", "10.00", "0"],
    ]
    cols = [
        "order_id", "order_date", "region", "channel", "category",
        "product", "quantity", "unit_price", "discount_pct",
    ]
    return pd.DataFrame(rows, columns=cols)


def test_clean_drops_invalid_rows(raw_df):
    cleaned, report = clean(raw_df)
    # ORD-3 (date), ORD-4 (qty), ORD-5 (price) removed -> 3 valid rows remain.
    assert len(cleaned) == 3
    assert report.invalid_date == 1
    assert report.invalid_quantity == 1
    assert report.invalid_price == 1
    assert set(cleaned["order_id"]) == {"ORD-1", "ORD-2", "ORD-6"}


def test_clean_normalises_and_fills(raw_df):
    cleaned, report = clean(raw_df)
    # region whitespace/case normalised to Title case
    assert cleaned.loc[cleaned["order_id"] == "ORD-1", "region"].iloc[0] == "North"
    # missing region filled
    assert cleaned.loc[cleaned["order_id"] == "ORD-2", "region"].iloc[0] == "Unknown"
    assert report.missing_region_filled == 1
    # channel lowercased
    assert cleaned.loc[cleaned["order_id"] == "ORD-1", "channel"].iloc[0] == "online"
    # dtypes coerced
    assert cleaned["quantity"].dtype.kind == "i"
    assert pd.api.types.is_datetime64_any_dtype(cleaned["order_date"])


def test_clean_removes_exact_duplicates(raw_df):
    dup = pd.concat([raw_df, raw_df.iloc[[0]]], ignore_index=True)
    cleaned, report = clean(dup)
    assert report.duplicates_removed == 1
    
    
def test_transform_revenue_math(raw_df):
    cleaned, _ = clean(raw_df)
    modelled = transform(cleaned)
    ord2 = modelled.loc[modelled["order_id"] == "ORD-2"].iloc[0]
    # 1 * 35.00 = 35 gross; 10% discount -> 31.50 net
    assert ord2["gross_revenue"] == 35.00
    assert ord2["net_revenue"] == 31.50
    # calendar dims
    assert ord2["year"] == 2023
    assert ord2["month"] == 1


def test_revenue_by_category_sorted(raw_df):
    modelled = transform(clean(raw_df)[0])
    cat = revenue_by_category(modelled)
    # Books: ORD-1 (20) + ORD-6 (30) = 50 ; Home: ORD-2 net 31.50
    assert cat.iloc[0]["category"] == "Books"
    assert cat.iloc[0]["net_revenue"] == 50.00
    # descending
    assert cat["net_revenue"].is_monotonic_decreasing


def test_monthly_revenue_ordering(raw_df):
    modelled = transform(clean(raw_df)[0])
    mth = monthly_revenue(modelled)
    assert list(mth["order_month"]) == sorted(mth["order_month"])
    # Jan: ORD-1 (20) + ORD-2 (31.50) = 51.50
    jan = mth.iloc[0]
    assert jan["net_revenue"] == 51.50


def test_load_to_sqlite_roundtrip(raw_df, tmp_path):
    modelled = transform(clean(raw_df)[0])
    db = tmp_path / "test.db"
    n = load_to_sqlite(modelled, db)
    assert n == len(modelled) == 3

    # table exists with expected row count
    back = query(db, f"SELECT COUNT(*) AS c FROM {FACT_TABLE}")
    assert int(back.iloc[0]["c"]) == 3

    # index was created
    with sqlite3.connect(db) as conn:
        idx = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
            (f"idx_{FACT_TABLE}_date",),
        ).fetchone()
    assert idx is not None

    # dates stored as ISO strings, sum of net revenue preserved
    total = query(db, f"SELECT ROUND(SUM(net_revenue),2) AS t FROM {FACT_TABLE}")
    assert float(total.iloc[0]["t"]) == pytest.approx(81.50)

