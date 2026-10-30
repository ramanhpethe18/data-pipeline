
"""Stage 5 - Analyse: summary stats + matplotlib charts read back from SQLite."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless / offline rendering
import matplotlib.pyplot as plt  # noqa: E402

from .load import FACT_TABLE, query  # noqa: E402


def summary_stats(db_path: str | Path) -> dict:
    """Compute headline KPIs directly in SQL against the fact table."""
    totals = query(
        db_path,
        f"""
        SELECT
            COUNT(*)                    AS orders,
            SUM(quantity)               AS units,
            ROUND(SUM(gross_revenue),2) AS gross_revenue,
            ROUND(SUM(net_revenue),2)   AS net_revenue,
            ROUND(AVG(net_revenue),2)   AS avg_order_value
        FROM {FACT_TABLE}
        """,
    ).iloc[0].to_dict()

    top_products = query(
        db_path,
        f"""
        SELECT product,
               ROUND(SUM(net_revenue),2) AS net_revenue,
               SUM(quantity)             AS units
        FROM {FACT_TABLE}
        GROUP BY product
        ORDER BY net_revenue DESC
        LIMIT 5
        """,
    )

    return {"totals": totals, "top_products": top_products}


def _revenue_by_category(db_path: str | Path):
    return query(
        db_path,
        f"""
        SELECT category, ROUND(SUM(net_revenue),2) AS net_revenue
        FROM {FACT_TABLE}
        GROUP BY category
        ORDER BY net_revenue DESC
        """,
    )


def _monthly_revenue(db_path: str | Path):
    return query(
        db_path,
        f"""
        SELECT order_month, ROUND(SUM(net_revenue),2) AS net_revenue
        FROM {FACT_TABLE}
        GROUP BY order_month
        ORDER BY order_month
        """,
    )
    
    
def make_charts(db_path: str | Path, out_dir: str | Path) -> list[Path]:
    """Render and save the analysis charts. Returns saved file paths."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []

    # Chart 1: revenue by category (bar).
    cat = _revenue_by_category(db_path)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(cat["category"], cat["net_revenue"], color="#2a6f97")
    ax.set_title("Net Revenue by Category")
    ax.set_xlabel("Category")
    ax.set_ylabel("Net Revenue ($)")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    p1 = out_dir / "revenue_by_category.png"
    fig.savefig(p1, dpi=120)
    plt.close(fig)
    saved.append(p1)

    # Chart 2: monthly revenue trend (line).
    mth = _monthly_revenue(db_path)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(mth["order_month"], mth["net_revenue"], marker="o", color="#e07a5f")
    ax.set_title("Monthly Net Revenue Trend")
    ax.set_xlabel("Month")
    ax.set_ylabel("Net Revenue ($)")
    ax.grid(alpha=0.3)
    fig.autofmt_xdate(rotation=45)
    fig.tight_layout()
    p2 = out_dir / "monthly_revenue.png"
    fig.savefig(p2, dpi=120)
    plt.close(fig)
    saved.append(p2)

    return saved

