
"""Stage 4 - Load: persist the modelled data into SQLite."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

FACT_TABLE = "fact_sales"


def load_to_sqlite(
    df: pd.DataFrame,
    db_path: str | Path,
    table: str = FACT_TABLE,
) -> int:
    """Write the transformed DataFrame to a SQLite table (replacing it).

    A supporting index on ``order_date`` is created for time-range queries.
    Returns the number of rows written.
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Store dates as ISO strings so the DB is portable and human-readable.
    out = df.copy()
    out["order_date"] = out["order_date"].dt.strftime("%Y-%m-%d")
    out["order_month"] = out["order_month"].dt.strftime("%Y-%m-%d")

    with sqlite3.connect(db_path) as conn:
        out.to_sql(table, conn, if_exists="replace", index=False)
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{table}_date ON {table}(order_date)"
        )
        conn.commit()
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    return int(count)


def query(db_path: str | Path, sql: str, params: tuple = ()) -> pd.DataFrame:
    """Run an arbitrary read query against the SQLite database."""
    with sqlite3.connect(Path(db_path)) as conn:
        return pd.read_sql_query(sql, conn, params=params)
