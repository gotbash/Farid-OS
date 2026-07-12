#!/usr/bin/env python3
"""Analyze Amazon Search Catalog Performance exports."""

from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from pathlib import Path


ALIASES = {
    "title": {"asin title", "title"},
    "asin": {"asin"},
    "impressions": {"impressions: impressions", "impressions"},
    "clicks": {"clicks: clicks", "clicks"},
    "cart_adds": {"cart adds: cart adds", "cart adds"},
    "purchases": {"purchases: purchases", "purchases"},
    "sales": {"purchases: search traffic sales", "search traffic sales", "sales"},
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


def fmt_money(value: float) -> str:
    return f"{value:,.2f}"


def load_rows(path: Path) -> tuple[list[dict[str, str]], dict[str, str], int]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        sample = list(csv.reader(handle))
    if not sample:
        raise ValueError("CSV has no header row")
    header_index = 0
    if sample[0] and "asin title" not in normalize(sample[0][0]):
        if len(sample) > 1 and any("asin title" in normalize(cell) for cell in sample[1]):
            header_index = 1
    fieldnames = sample[header_index]
    columns = resolve_columns(fieldnames)
    rows = [dict(zip(fieldnames, row)) for row in sample[header_index + 1 :]]
    return rows, columns, header_index


def analyze(path: Path) -> str:
    rows, columns, _header_index = load_rows(path)
    if not rows:
        raise ValueError("CSV contains no data rows")

    parsed = []
    invalid = []
    for line_number, row in enumerate(rows, start=2):
        try:
            item = {
                "title": (row.get(columns["title"]) or "").strip(),
                "asin": (row.get(columns["asin"]) or "").strip(),
            }
            for metric in ("impressions", "clicks", "cart_adds", "purchases", "sales"):
                item[metric] = parse_number(row.get(columns[metric], ""))
            if not item["asin"]:
                raise ValueError("empty ASIN")
            if item["clicks"] > item["impressions"]:
                raise ValueError("clicks exceed impressions")
            parsed.append(item)
        except ValueError as exc:
            invalid.append((line_number, str(exc)))

    if not parsed:
        raise ValueError("No valid rows remain after validation")

    totals = {metric: sum(row[metric] for row in parsed) for metric in ("impressions", "clicks", "cart_adds", "purchases", "sales")}
    top_by_sales = sorted(parsed, key=lambda row: row["sales"], reverse=True)[:10]
    low_ctr = sorted(
        (row for row in parsed if row["impressions"] >= 500 and pct(row["clicks"], row["impressions"]) is not None),
        key=lambda row: pct(row["clicks"], row["impressions"]) or 0,
    )[:10]
    strong_conversion = sorted(
        (row for row in parsed if row["clicks"] >= 5 and pct(row["purchases"], row["clicks"]) is not None),
        key=lambda row: pct(row["purchases"], row["clicks"]) or 0,
        reverse=True,
    )[:10]

    lines = [
        "# Search Catalog Performance Analysis",
        "",
        f"Source: `{path.name}`",
        "",
        "## Data quality",
        "",
        f"- Input rows: {len(rows)}",
        f"- Valid rows: {len(parsed)}",
        f"- Invalid rows excluded: {len(invalid)}",
        "",
        "## Catalog funnel summary",
        "",
        f"- Impressions: {fmt_int(totals['impressions'])}",
        f"- Clicks: {fmt_int(totals['clicks'])}",
        f"- Cart adds: {fmt_int(totals['cart_adds'])}",
        f"- Purchases: {fmt_int(totals['purchases'])}",
        f"- Search traffic sales: {fmt_money(totals['sales'])}",
        f"- CTR: {fmt_pct(pct(totals['clicks'], totals['impressions']))}",
        f"- Click-to-purchase: {fmt_pct(pct(totals['purchases'], totals['clicks']))}",
        "",
        "## Top ASINs by search traffic sales",
        "",
    ]
    lines.extend(
        f"- `{row['asin']}` - sales {fmt_money(row['sales'])}, impressions {fmt_int(row['impressions'])}, clicks {fmt_int(row['clicks'])}, purchases {fmt_int(row['purchases'])}"
        for row in top_by_sales
    )
    lines.extend(["", "## Low-CTR ASINs with visibility", ""])
    lines.extend(
        f"- `{row['asin']}` - CTR {fmt_pct(pct(row['clicks'], row['impressions']))}, impressions {fmt_int(row['impressions'])}, clicks {fmt_int(row['clicks'])}"
        for row in low_ctr
    )
    lines.extend(["", "## Strong post-click ASINs", ""])
    lines.extend(
        f"- `{row['asin']}` - click-to-purchase {fmt_pct(pct(row['purchases'], row['clicks']))}, clicks {fmt_int(row['clicks'])}, purchases {fmt_int(row['purchases'])}"
        for row in strong_conversion
    )
    lines.extend([
        "",
        "## Recommended actions",
        "",
        "- Use low-CTR visible ASINs for image/title/offer review.",
        "- Protect strong post-click ASINs in PPC and organic content work.",
        "- Compare ASIN-level Search Catalog Performance against SQP and Search Term Report before changing bids.",
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
