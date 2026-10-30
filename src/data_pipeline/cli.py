
"""Command-line entry point orchestrating the full ETL + analytics pipeline.

Usage:
    python -m data_pipeline.cli run --input data/sample_sales.csv
    python -m data_pipeline.cli generate --rows 1000
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .analyze import make_charts, summary_stats
from .clean import clean
from .generate_data import write_csv
from .ingest import ingest
from .load import load_to_sqlite
from .transform import transform


def _fmt_money(value) -> str:
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value)


def run_pipeline(input_csv: Path, db_path: Path, out_dir: Path) -> dict:
    """Execute ingest -> clean -> transform -> load -> analyse."""
    print(f"[1/5] Ingest    : reading {input_csv}")
    raw = ingest(input_csv)
    print(f"        {len(raw)} raw rows loaded")

    print("[2/5] Clean     : validating and normalising")
    cleaned, report = clean(raw)
    for k, v in report.as_dict().items():
        print(f"        {k:<24}: {v}")
    for note in report.notes:
        print(f"        note: {note}")

    print("[3/5] Transform : deriving revenue metrics")
    modelled = transform(cleaned)

    print(f"[4/5] Load      : writing SQLite -> {db_path}")
    n = load_to_sqlite(modelled, db_path)
    print(f"        {n} rows persisted to fact_sales")

    print("[5/5] Analyse   : summary stats + charts")
    stats = summary_stats(db_path)
    totals = stats["totals"]
    print(f"        orders          : {int(totals['orders'])}")
    print(f"        units sold      : {int(totals['units'])}")
    print(f"        gross revenue   : {_fmt_money(totals['gross_revenue'])}")
    print(f"        net revenue     : {_fmt_money(totals['net_revenue'])}")
    print(f"        avg order value : {_fmt_money(totals['avg_order_value'])}")
    print("        top products    :")
    for _, row in stats["top_products"].iterrows():
        print(
            f"          - {row['product']:<15} "
            f"{_fmt_money(row['net_revenue']):>12}  ({int(row['units'])} units)"
        )

    charts = make_charts(db_path, out_dir)
    for c in charts:
        print(f"        chart saved     : {c}")

    print("\nPipeline complete.")
    return {"rows": n, "report": report.as_dict(), "charts": [str(c) for c in charts]}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="data_pipeline",
        description="ETL + analytics pipeline (ingest -> clean -> transform -> load -> analyse).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run the full pipeline.")
    run_p.add_argument("--input", type=Path, default=Path("data/sample_sales.csv"))
    run_p.add_argument("--db", type=Path, default=Path("output/sales.db"))
    run_p.add_argument("--out", type=Path, default=Path("output"))

    gen_p = sub.add_parser("generate", help="Regenerate the sample raw CSV.")
    gen_p.add_argument("--out", type=Path, default=Path("data/sample_sales.csv"))
    gen_p.add_argument("--rows", type=int, default=1000)
    gen_p.add_argument("--seed", type=int, default=42)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "generate":
        path = write_csv(args.out, args.rows, args.seed)
        print(f"Wrote {args.rows} rows -> {path}")
        return 0

    if args.command == "run":
        if not args.input.exists():
            print(f"error: input CSV not found: {args.input}", file=sys.stderr)
            print("hint: run 'python -m data_pipeline.cli generate' first.", file=sys.stderr)
            return 1
        run_pipeline(args.input, args.db, args.out)
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())

