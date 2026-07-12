#!/usr/bin/env python3
"""Analyze an Amazon Search Term Report CSV using only the Python standard library."""

from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from pathlib import Path


ALIASES = {
    "search_term": {"customer search term", "search term", "query"},
    "impressions": {"impressions"},
    "clicks": {"clicks"},
    "spend": {"spend", "cost"},
    "sales": {"7 day total sales", "14 day total sales", "sales", "sales usd"},
    "orders": {"7 day total orders (#)", "14 day total orders (#)", "orders", "purchases"},
}
REQUIRED = tuple(ALIASES)


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def parse_number(value: str) -> float:
    cleaned = re.sub(r"[^0-9.()\-]", "", (value or "").replace(",", ""))
    if not cleaned:
        return 0.0
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = f"-{cleaned[1:-1]}"
    number = float(cleaned)
    if not math.isfinite(number) or number < 0:
        raise ValueError(value)
    return number


def resolve_columns(fieldnames: list[str]) -> dict[str, str]:
    normalized = {normalize(name): name for name in fieldnames}
    resolved = {}
    for canonical, aliases in ALIASES.items():
        for alias in aliases:
            if normalize(alias) in normalized:
                resolved[canonical] = normalized[normalize(alias)]
                break
    missing = [column for column in REQUIRED if column not in resolved]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))
    return resolved


def pct(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator else None


def fmt_pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1%}"


def fmt_money(value: float) -> str:
    return f"{value:,.2f}"


def analyze(path: Path, acos_limit: float, waste_clicks: int) -> str:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV has no header row")
        columns = resolve_columns(reader.fieldnames)
        rows = list(reader)

    if not rows:
        raise ValueError("CSV contains no data rows")

    parsed = []
    invalid_rows = []
    for line_number, row in enumerate(rows, start=2):
        try:
            item = {"search_term": (row.get(columns["search_term"]) or "").strip()}
            for metric in ("impressions", "clicks", "spend", "sales", "orders"):
                item[metric] = parse_number(row.get(columns[metric], ""))
            if not item["search_term"]:
                raise ValueError("empty search term")
            if item["clicks"] > item["impressions"]:
                raise ValueError("clicks exceed impressions")
            parsed.append(item)
        except ValueError as exc:
            invalid_rows.append((line_number, str(exc)))

    if not parsed:
        raise ValueError("No valid rows remain after validation")

    totals = {metric: sum(row[metric] for row in parsed) for metric in ("impressions", "clicks", "spend", "sales", "orders")}
    no_sales = sorted(
        (row for row in parsed if row["sales"] == 0 and row["clicks"] >= waste_clicks),
        key=lambda row: row["spend"], reverse=True,
    )
    high_acos = sorted(
        (row for row in parsed if row["sales"] > 0 and row["spend"] / row["sales"] > acos_limit),
        key=lambda row: row["spend"] / row["sales"], reverse=True,
    )
    harvest = sorted(
        (row for row in parsed if row["orders"] >= 2 and row["sales"] > 0 and row["spend"] / row["sales"] <= 0.30),
        key=lambda row: row["sales"], reverse=True,
    )

    lines = [
        "# Amazon Search Term Report Analysis",
        "",
        f"Source: `{path.name}`",
        "",
        "## Data quality",
        "",
        f"- Input rows: {len(rows)}",
        f"- Valid rows: {len(parsed)}",
        f"- Invalid rows excluded: {len(invalid_rows)}",
        f"- Grain assumption: one row per exported search-term record; duplicate terms are intentionally aggregated only in totals.",
        "",
        "## Account summary",
        "",
        f"- Impressions: {totals['impressions']:,.0f}",
        f"- Clicks: {totals['clicks']:,.0f}",
        f"- Spend: {fmt_money(totals['spend'])}",
        f"- Sales: {fmt_money(totals['sales'])}",
        f"- Orders: {totals['orders']:,.0f}",
        f"- CTR: {fmt_pct(pct(totals['clicks'], totals['impressions']))}",
        f"- CVR: {fmt_pct(pct(totals['orders'], totals['clicks']))}",
        f"- CPC: {fmt_money(pct(totals['spend'], totals['clicks']) or 0)}",
        f"- ACOS: {fmt_pct(pct(totals['spend'], totals['sales']))}",
        "- TACoS: [MISSING — total Amazon sales are not present in a Search Term Report]",
        "",
        f"## Waste candidates — ≥{waste_clicks} clicks and zero attributed sales",
        "",
    ]
    lines.extend(f"- `{r['search_term']}` — clicks {r['clicks']:.0f}, spend {fmt_money(r['spend'])}" for r in no_sales[:20])
    if not no_sales:
        lines.append("- None detected under the configured rule.")
    lines.extend(["", f"## High-ACOS terms — above {acos_limit:.0%}", ""])
    lines.extend(f"- `{r['search_term']}` — ACOS {fmt_pct(r['spend']/r['sales'])}, spend {fmt_money(r['spend'])}, sales {fmt_money(r['sales'])}" for r in high_acos[:20])
    if not high_acos:
        lines.append("- None detected under the configured rule.")
    lines.extend(["", "## Harvest candidates — ≥2 orders and ACOS ≤30%", ""])
    lines.extend(f"- `{r['search_term']}` — orders {r['orders']:.0f}, ACOS {fmt_pct(r['spend']/r['sales'])}" for r in harvest[:20])
    if not harvest:
        lines.append("- None detected under the configured rule.")
    lines.extend([
        "", "## Guardrails", "",
        "- These are rule-based review candidates, not automatic bid or negative-keyword changes.",
        "- Confirm match type, targeting role, attribution window, margin, rank, and launch stage before action.",
        "- Resolve the TACoS marker by supplying total Amazon sales from Business Reports.",
    ])
    if invalid_rows:
        lines.extend(["", "## Excluded rows", ""])
        lines.extend(f"- Line {line}: {reason}" for line, reason in invalid_rows[:20])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--acos-limit", type=float, default=0.40)
    parser.add_argument("--waste-clicks", type=int, default=8)
    args = parser.parse_args()
    try:
        report = analyze(args.csv_path.expanduser().resolve(), args.acos_limit, args.waste_clicks)
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

