
"""Stage 3 - Transform: derive business metrics with pandas."""
from __future__ import annotations

import pandas as pd


def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived revenue columns and calendar dimensions.

    Derived columns:
      * ``gross_revenue``  = quantity * unit_price
      * ``net_revenue``    = gross_revenue * (1 - discount_pct/100)
      * ``order_month``    = period start (first of month) for time series
      * ``year`` / ``month``
    """
    df = df.copy()

    df["gross_revenue"] = (df["quantity"] * df["unit_price"]).round(2)
    df["net_revenue"] = (
        df["gross_revenue"] * (1 - df["discount_pct"] / 100.0)
    ).round(2)

    df["order_month"] = df["order_date"].dt.to_period("M").dt.to_timestamp()
    df["year"] = df["order_date"].dt.year.astype(int)
    df["month"] = df["order_date"].dt.month.astype(int)

    return df



def revenue_by_category(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate net revenue and units by category, sorted descending."""
    out = (
        df.groupby("category", as_index=False)
        .agg(
            net_revenue=("net_revenue", "sum"),
            gross_revenue=("gross_revenue", "sum"),
            units=("quantity", "sum"),
            orders=("order_id", "count"),
        )
        .sort_values("net_revenue", ascending=False)
        .reset_index(drop=True)
    )
    out["net_revenue"] = out["net_revenue"].round(2)
    out["gross_revenue"] = out["gross_revenue"].round(2)
    return out


def monthly_revenue(df: pd.DataFrame) -> pd.DataFrame:
    """Net revenue per calendar month, chronologically ordered."""
    out = (
        df.groupby("order_month", as_index=False)
        .agg(net_revenue=("net_revenue", "sum"), orders=("order_id", "count"))
        .sort_values("order_month")
        .reset_index(drop=True)
    )
    out["net_revenue"] = out["net_revenue"].round(2)
    return out


def revenue_by_region(df: pd.DataFrame) -> pd.DataFrame:
    """Net revenue by region, sorted descending."""
    out = (
        df.groupby("region", as_index=False)
        .agg(net_revenue=("net_revenue", "sum"), orders=("order_id", "count"))
        .sort_values("net_revenue", ascending=False)
        .reset_index(drop=True)
    )
    out["net_revenue"] = out["net_revenue"].round(2)
    return out

