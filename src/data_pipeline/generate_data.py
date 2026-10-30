
"""Deterministically generate a realistic raw sales CSV.

The generated file intentionally contains messy, real-world artifacts
(missing values, inconsistent casing, whitespace, duplicates, a couple of
invalid rows) so the cleaning/validation stage has something to do.
"""
from __future__ import annotations

import argparse
import csv
import random
from datetime import date, timedelta
from pathlib import Path

REGIONS = ["North", "South", "East", "West"]
CATEGORIES = {
    "Electronics": ["Laptop", "Headphones", "Monitor", "Keyboard", "Webcam"],
    "Home": ["Blender", "Lamp", "Cookware Set", "Vacuum", "Chair"],
    "Sports": ["Yoga Mat", "Dumbbell", "Running Shoes", "Bicycle", "Tennis Racket"],
    "Books": ["Novel", "Cookbook", "Biography", "Textbook", "Comic"],
}
CHANNELS = ["online", "in-store", "partner"]
BASE_PRICE = {
    "Laptop": 950, "Headphones": 120, "Monitor": 240, "Keyboard": 55, "Webcam": 70,
    "Blender": 80, "Lamp": 35, "Cookware Set": 130, "Vacuum": 210, "Chair": 95,
    "Yoga Mat": 25, "Dumbbell": 40, "Running Shoes": 110, "Bicycle": 520,
    "Tennis Racket": 85, "Novel": 15, "Cookbook": 28, "Biography": 22,
    "Textbook": 90, "Comic": 12,
}


def generate(rows: int, seed: int = 42) -> list[dict]:
    rng = random.Random(seed)
    start = date(2023, 1, 1)
    records: list[dict] = []

    for i in range(rows):
        category = rng.choice(list(CATEGORIES))
        product = rng.choice(CATEGORIES[category])
        region = rng.choice(REGIONS)
        channel = rng.choice(CHANNELS)
        order_day = start + timedelta(days=rng.randint(0, 364))
        qty = rng.randint(1, 8)

        # price wobbles around the base with occasional discounts
        price = round(BASE_PRICE[product] * rng.uniform(0.9, 1.15), 2)
        discount = rng.choice([0, 0, 0, 5, 10, 15])

        # Introduce messy, inconsistent formatting on purpose.
        region_raw = rng.choice([region, region.upper(), f" {region} ", region.lower()])
        channel_raw = rng.choice([channel, channel.upper(), channel.title()])

        record = {
            "order_id": f"ORD-{10000 + i}",
            "order_date": order_day.isoformat(),
            "region": region_raw,
            "channel": channel_raw,
            "category": category,
            "product": product,
            "quantity": qty,
            "unit_price": price,
            "discount_pct": discount,
        }

        # ~4% missing region, ~3% missing unit_price
        if rng.random() < 0.04:
            record["region"] = ""
        if rng.random() < 0.03:
            record["unit_price"] = ""

        records.append(record)

    # A few invalid rows the validator must drop.
    records.append({
        "order_id": "ORD-BAD1", "order_date": "2023-13-40", "region": "North",
        "channel": "online", "category": "Electronics", "product": "Laptop",
        "quantity": 2, "unit_price": 900, "discount_pct": 0,
    })
    records.append({
        "order_id": "ORD-BAD2", "order_date": "2023-06-15", "region": "West",
        "channel": "online", "category": "Home", "product": "Lamp",
        "quantity": -3, "unit_price": 35, "discount_pct": 0,
    })

    # Exact duplicate of the first record.
    records.append(dict(records[0]))
    return records


FIELDNAMES = [
    "order_id", "order_date", "region", "channel", "category",
    "product", "quantity", "unit_price", "discount_pct",
]


def write_csv(path: Path, rows: int = 1000, seed: int = 42) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    records = generate(rows, seed)

    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(records)

    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a raw sales CSV.")
    parser.add_argument("--out", default="data/sample_sales.csv", type=Path)
    parser.add_argument("--rows", default=1000, type=int)
    parser.add_argument("--seed", default=42, type=int)

    args = parser.parse_args()
    out = write_csv(args.out, args.rows, args.seed)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
