#!/usr/bin/env python3
"""Analyze Amazon Sponsored Products Campaign reports."""

from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from pathlib import Path


ALIASES = {
    "campaign": {"campaign name"},
    "status": {"status"},
    "budget": {"budget amount"},
    "targeting_type": {"targeting type"},
    "impressions": {"impressions"},
    "clicks": {"clicks"},
    "spend": {"spend"},
    "sales": {"7 day total sales", "14 day total sales", "sales"},
    "orders": {"7 day total orders (#)", "14 day total orders (#)", "orders"},
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


def fmt_money(value: float) -> str:
    return f"{value:,.2f}"


def analyze(path: Path, acos_limit: float = 0.40) -> str:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV has no header row")
        columns = resolve_columns(reader.fieldnames)
        rows = list(reader)
    if not rows:
        raise ValueError("CSV contains no data rows")

    parsed = []
    invalid = []
    for line_number, row in enumerate(rows, start=2):
        try:
            item = {
                "campaign": (row.get(columns["campaign"]) or "").strip(),
                "status": (row.get(columns["status"]) or "").strip(),
                "targeting_type": (row.get(columns["targeting_type"]) or "").strip(),
            }
            for metric in ("budget", "impressions", "clicks", "spend", "sales", "orders"):
                item[metric] = parse_number(row.get(columns[metric], ""))
            if not item["campaign"]:
                raise ValueError("empty campaign")
            if item["clicks"] > item["impressions"]:
                raise ValueError("clicks exceed impressions")
            parsed.append(item)
        except ValueError as exc:
            invalid.append((line_number, str(exc)))

    totals = {metric: sum(row[metric] for row in parsed) for metric in ("budget", "impressions", "clicks", "spend", "sales", "orders")}
    high_spend_no_sales = sorted(
        (row for row in parsed if row["spend"] > 0 and row["sales"] == 0),
        key=lambda row: row["spend"],
        reverse=True,
    )
    high_acos = sorted(
        (row for row in parsed if row["sales"] > 0 and pct(row["spend"], row["sales"]) and pct(row["spend"], row["sales"]) > acos_limit),
        key=lambda row: pct(row["spend"], row["sales"]) or 0,
        reverse=True,
    )
    strong = sorted(
        (row for row in parsed if row["orders"] >= 1 and row["sales"] > 0 and (pct(row["spend"], row["sales"]) or 0) <= 0.30),
        key=lambda row: row["sales"],
        reverse=True,
    )

    lines = [
        "# Sponsored Products Campaign Report Analysis",
        "",
        f"Source: `{path.name}`",
        "",
        "## Data quality",
        "",
        f"- Input rows: {len(rows)}",
        f"- Valid rows: {len(parsed)}",
        f"- Invalid rows excluded: {len(invalid)}",
        "",
        "## Campaign summary",
        "",
        f"- Campaigns: {len(parsed):,}",
        f"- Impressions: {totals['impressions']:,.0f}",
        f"- Clicks: {totals['clicks']:,.0f}",
        f"- Spend: {fmt_money(totals['spend'])}",
        f"- Sales: {fmt_money(totals['sales'])}",
        f"- Orders: {totals['orders']:,.0f}",
        f"- CTR: {fmt_pct(pct(totals['clicks'], totals['impressions']))}",
        f"- CVR: {fmt_pct(pct(totals['orders'], totals['clicks']))}",
        f"- CPC: {fmt_money(pct(totals['spend'], totals['clicks']) or 0)}",
        f"- ACOS: {fmt_pct(pct(totals['spend'], totals['sales']))}",
        "",
        "## Spend with zero attributed sales",
        "",
    ]
    if high_spend_no_sales:
        lines.extend(
            f"- `{row['campaign']}` - spend {fmt_money(row['spend'])}, clicks {row['clicks']:.0f}, targeting {row['targeting_type']}"
            for row in high_spend_no_sales[:15]
        )
    else:
        lines.append("- None detected.")
    lines.extend(["", f"## High-ACOS campaigns above {acos_limit:.0%}", ""])
    if high_acos:
        lines.extend(
            f"- `{row['campaign']}` - ACOS {fmt_pct(pct(row['spend'], row['sales']))}, spend {fmt_money(row['spend'])}, sales {fmt_money(row['sales'])}, orders {row['orders']:.0f}"
            for row in high_acos[:15]
        )
    else:
        lines.append("- None detected.")
    lines.extend(["", "## Strong campaigns", ""])
    if strong:
        lines.extend(
            f"- `{row['campaign']}` - ACOS {fmt_pct(pct(row['spend'], row['sales']))}, sales {fmt_money(row['sales'])}, orders {row['orders']:.0f}"
            for row in strong[:15]
        )
    else:
        lines.append("- None detected under the current rule.")
    lines.extend([
        "",
        "## Recommended actions",
        "",
        "- Use this report to map search-term issues back to campaign-level spend and structure.",
        "- Pull Targeting report before changing bids if campaign-level data is too broad.",
        "- Separate budget pacing issues from bid efficiency issues before action.",
    ])
    if invalid:
        lines.extend(["", "## Excluded rows", ""])
        lines.extend(f"- Line {line}: {reason}" for line, reason in invalid[:20])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--acos-limit", type=float, default=0.40)
    args = parser.parse_args()
    try:
        report = analyze(args.csv_path.expanduser().resolve(), args.acos_limit)
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
