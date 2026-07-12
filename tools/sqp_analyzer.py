#!/usr/bin/env python3
"""Analyze Amazon Search Query Performance exports from Brand Analytics."""

from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from pathlib import Path


ALIASES = {
    "search_query": {"search_query", "search query", "query", "search term"},
    "impressions": {"impressions", "impressions: total count", "search funnel - impressions"},
    "clicks": {"clicks", "clicks: total count", "search funnel - clicks"},
    "cart_adds": {"cart_adds", "cart adds", "cart adds: total count", "search funnel - cart adds"},
    "purchases": {"purchases", "orders", "purchases: total count", "search funnel - purchases"},
}


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def parse_number(value: str) -> float:
    cleaned = re.sub(r"[^0-9.()\-]", "", (value or "").replace(",", ""))
    if not cleaned:
        return 0.0
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = f"-{cleaned[1:-1]}"
    number = float(cleaned)
    if not math.isfinite(number):
        raise ValueError(value)
    return number


def resolve_columns(fieldnames: list[str]) -> dict[str, str]:
    normalized = {normalize(name): name for name in fieldnames}
    resolved: dict[str, str] = {}
    for canonical, aliases in ALIASES.items():
        for alias in aliases:
            if normalize(alias) in normalized:
                resolved[canonical] = normalized[normalize(alias)]
                break
    missing = [key for key in ALIASES if key not in resolved]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))
    return resolved


def pct(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator else None


def fmt_pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1%}"


def fmt_int(value: float) -> str:
    return f"{value:,.0f}"


def analyze(path: Path) -> str:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        sample = list(csv.reader(handle))
        if not sample:
            raise ValueError("CSV has no header row")
        header_index = 0
        if sample[0] and "search query" not in normalize(sample[0][0]):
            if len(sample) > 1 and any("search query" in normalize(cell) for cell in sample[1]):
                header_index = 1
        fieldnames = sample[header_index]
        columns = resolve_columns(fieldnames)
        rows = [dict(zip(fieldnames, row)) for row in sample[header_index + 1 :]]

    if not rows:
        raise ValueError("CSV contains no data rows")

    parsed = []
    invalid = []
    for line_number, row in enumerate(rows, start=2):
        try:
            item = {"search_query": (row.get(columns["search_query"]) or "").strip()}
            for metric in ("impressions", "clicks", "cart_adds", "purchases"):
                item[metric] = parse_number(row.get(columns[metric], ""))
            if not item["search_query"]:
                raise ValueError("empty search query")
            if item["clicks"] > item["impressions"]:
                raise ValueError("clicks exceed impressions")
            parsed.append(item)
        except ValueError as exc:
            invalid.append((line_number, str(exc)))

    if not parsed:
        raise ValueError("No valid rows remain after validation")

    totals = {metric: sum(row[metric] for row in parsed) for metric in ("impressions", "clicks", "cart_adds", "purchases")}
    top_queries = sorted(parsed, key=lambda row: row["impressions"], reverse=True)[:10]
    weak_queries = sorted(
        (row for row in parsed if row["impressions"] >= 1000 and row["clicks"] == 0),
        key=lambda row: row["impressions"],
        reverse=True,
    )
    strong_queries = sorted(
        (
            row
            for row in parsed
            if row["purchases"] >= 1
            and pct(row["purchases"], row["clicks"]) is not None
            and pct(row["purchases"], row["clicks"]) >= 0.1
        ),
        key=lambda row: row["purchases"],
        reverse=True,
    )

    lines = [
        "# Amazon Search Query Performance Analysis",
        "",
        f"Source: `{path.name}`",
        "",
        "## Data quality",
        "",
        f"- Input rows: {len(rows)}",
        f"- Valid rows: {len(parsed)}",
        f"- Invalid rows excluded: {len(invalid)}",
        "",
        "## Funnel summary",
        "",
        f"- Impressions: {fmt_int(totals['impressions'])}",
        f"- Clicks: {fmt_int(totals['clicks'])}",
        f"- Cart adds: {fmt_int(totals['cart_adds'])}",
        f"- Purchases: {fmt_int(totals['purchases'])}",
        f"- CTR: {fmt_pct(pct(totals['clicks'], totals['impressions']))}",
        f"- Click-to-cart: {fmt_pct(pct(totals['cart_adds'], totals['clicks']))}",
        f"- Click-to-purchase: {fmt_pct(pct(totals['purchases'], totals['clicks']))}",
        "- TACoS: [MISSING — total Amazon sales are not present in this Search Query Performance export]",
        "",
        "## Top queries by impressions",
        "",
    ]
    lines.extend(
        f"- `{row['search_query']}` — impressions {fmt_int(row['impressions'])}, clicks {fmt_int(row['clicks'])}, cart adds {fmt_int(row['cart_adds'])}, purchases {fmt_int(row['purchases'])}"
        for row in top_queries
    )
    lines.extend(["", "## Weak queries", ""])
    if weak_queries:
        lines.extend(f"- `{row['search_query']}` — {fmt_int(row['impressions'])} impressions, no clicks" for row in weak_queries[:20])
    else:
        lines.append("- None detected under the current rule.")
    lines.extend(["", "## Strong queries", ""])
    if strong_queries:
        lines.extend(
            f"- `{row['search_query']}` — purchases {fmt_int(row['purchases'])}, click-to-purchase {fmt_pct(pct(row['purchases'], row['clicks']))}"
            for row in strong_queries[:20]
        )
    else:
        lines.append("- None detected under the current rule.")
    lines.extend([
        "",
        "## Guardrails",
        "",
        "- This is a directional funnel analysis, not an automatic optimization engine.",
        "- Compare against paid search term analysis, placement data, and inventory context before changing bids or targeting.",
        "- Use the Search Query Performance export's date range and price fields as supporting context only.",
    ])
    if invalid:
        lines.extend(["", "## Excluded rows", ""])
        lines.extend(f"- Line {line}: {reason}" for line, reason in invalid[:20])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = analyze(args.csv_path.expanduser().resolve())
    except (OSError, ValueError, csv.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if args.output:
        args.output.write_text(report, encoding="utf-8")
        print(args.output)
    else:
        print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
