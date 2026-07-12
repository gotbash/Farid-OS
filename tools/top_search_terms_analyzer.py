#!/usr/bin/env python3
"""Analyze Amazon Brand Analytics Top Search Terms exports."""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path


def normalize(value: str) -> str:
    return " ".join(value.strip().lower().split())


def parse_float(value: str) -> float:
    try:
        return float((value or "").replace(",", ""))
    except ValueError:
        return 0.0


def read_rows(path: Path, limit: int) -> tuple[list[dict[str, str]], list[str], int, bool]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        first = next(reader, None)
        if first is None:
            raise ValueError("CSV has no rows")
        if first and normalize(first[0]) == "search frequency rank":
            fieldnames = first
        else:
            fieldnames = next(reader, None)
            if fieldnames is None:
                raise ValueError("CSV has no header row")
        rows = []
        scanned = 0
        for raw_row in reader:
            scanned += 1
            rows.append(dict(zip(fieldnames, raw_row)))
            if len(rows) >= limit:
                break
        truncated = len(rows) >= limit
        return rows, fieldnames, scanned, truncated


def analyze(path: Path, limit: int = 100) -> str:
    rows, fieldnames, scanned, truncated = read_rows(path, limit)
    normalized = {normalize(name): name for name in fieldnames}
    required = ["search frequency rank", "search term", "top clicked brand #1", "top clicked product #1: asin"]
    missing = [name for name in required if name not in normalized]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))

    rank_col = normalized["search frequency rank"]
    term_col = normalized["search term"]
    brand_cols = [fieldnames_by_name for key, fieldnames_by_name in normalized.items() if key.startswith("top clicked brand")]
    category_cols = [fieldnames_by_name for key, fieldnames_by_name in normalized.items() if key.startswith("top clicked category")]
    product_cols = [fieldnames_by_name for key, fieldnames_by_name in normalized.items() if key.endswith(": asin")]
    click_share_col = normalized.get("top clicked product #1: click share")
    conversion_share_col = normalized.get("top clicked product #1: conversion share")

    brand_counter: Counter[str] = Counter()
    category_counter: Counter[str] = Counter()
    product_counter: Counter[str] = Counter()
    top_terms = []
    high_click_share = []

    for row in rows:
        term = (row.get(term_col) or "").strip()
        rank = (row.get(rank_col) or "").strip()
        if term:
            top_terms.append((rank, term))
        for column in brand_cols:
            value = (row.get(column) or "").strip()
            if value:
                brand_counter[value] += 1
        for column in category_cols:
            value = (row.get(column) or "").strip()
            if value:
                category_counter[value] += 1
        for column in product_cols:
            value = (row.get(column) or "").strip()
            if value:
                product_counter[value] += 1
        if click_share_col:
            click_share = parse_float(row.get(click_share_col, ""))
            if click_share >= 5:
                high_click_share.append((click_share, term, row.get(normalized["top clicked product #1: asin"], "")))

    high_click_share.sort(reverse=True)

    lines = [
        "# Top Search Terms Analysis",
        "",
        f"Source: `{path.name}`",
        "",
        "## Data quality",
        "",
        f"- Rows scanned: {scanned:,}",
        f"- Rows analyzed in detail: {len(rows):,}",
        f"- Truncated: {'yes' if truncated else 'no'}",
        "- Grain: Brand Analytics top search terms; this is not an Amazon Ads Search Term Report.",
        "- Spend, sales, ACOS, CPC, and campaign data are not available in this export.",
        "",
        "## Top search terms",
        "",
    ]
    lines.extend(f"- #{rank} `{term}`" for rank, term in top_terms[:20])
    lines.extend(["", "## Most frequent top-clicked brands in analyzed rows", ""])
    lines.extend(f"- `{brand}` - appears {count} times" for brand, count in brand_counter.most_common(15))
    lines.extend(["", "## Most frequent categories in analyzed rows", ""])
    lines.extend(f"- `{category}` - appears {count} times" for category, count in category_counter.most_common(15))
    lines.extend(["", "## Most frequent top-clicked ASINs in analyzed rows", ""])
    lines.extend(f"- `{asin}` - appears {count} times" for asin, count in product_counter.most_common(15))
    lines.extend(["", "## High click-share winners", ""])
    if high_click_share:
        lines.extend(f"- `{asin}` on `{term}` - click share {share:.2f}%" for share, term, asin in high_click_share[:15])
    else:
        lines.append("- None detected under the current rule.")
    lines.extend([
        "",
        "## Recommended actions",
        "",
        "- Use this report for competitor and category intelligence, not PPC efficiency decisions.",
        "- Cross-check relevant terms against SQP and Amazon Ads Search Term Report before changing bids.",
        "- Prioritize repeated competitor ASINs and high click-share winners for listing and positioning review.",
    ])
    if conversion_share_col:
        lines.extend(["", "## Available conversion-share field", "", f"- `{conversion_share_col}` is present for deeper analysis."])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = analyze(args.csv_path.expanduser().resolve(), args.limit)
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
