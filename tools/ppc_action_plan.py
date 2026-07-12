#!/usr/bin/env python3
"""Create a PPC action plan from Sponsored Products search term, campaign, and targeting reports."""

from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from pathlib import Path

import campaign_analyzer
import search_term_analyzer
import targeting_analyzer


DEFAULT_REPORTS_DIR = Path("~/Downloads/Rubex/Reports").expanduser()


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


def pct(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator else None


def fmt_pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1%}"


def fmt_money(value: float) -> str:
    return f"{value:,.2f}"


def latest_matching(reports_dir: Path, patterns: tuple[str, ...]) -> Path:
    files = [
        path
        for path in reports_dir.expanduser().iterdir()
        if path.is_file() and any(pattern.lower() in path.name.lower() for pattern in patterns)
    ]
    if not files:
        raise ValueError("Missing report matching: " + ", ".join(patterns))
    return max(files, key=lambda path: path.stat().st_mtime)


def parse_search_terms(path: Path) -> list[dict[str, float | str]]:
    fieldnames, rows = search_term_analyzer.load_table(path)
    columns = search_term_analyzer.resolve_columns(fieldnames)
    parsed = []
    for row in rows:
        item: dict[str, float | str] = {"search_term": (row.get(columns["search_term"]) or "").strip()}
        for metric in ("impressions", "clicks", "spend", "sales", "orders"):
            item[metric] = parse_number(row.get(columns[metric], ""))
        if item["search_term"]:
            parsed.append(item)
    return parsed


def parse_campaigns(path: Path) -> list[dict[str, float | str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("Campaign report has no header row")
        columns = campaign_analyzer.resolve_columns(reader.fieldnames)
        rows = list(reader)
    parsed = []
    for row in rows:
        item: dict[str, float | str] = {
            "campaign": (row.get(columns["campaign"]) or "").strip(),
            "status": (row.get(columns["status"]) or "").strip(),
            "targeting_type": (row.get(columns["targeting_type"]) or "").strip(),
        }
        for metric in ("budget", "impressions", "clicks", "spend", "sales", "orders"):
            item[metric] = parse_number(row.get(columns[metric], ""))
        if item["campaign"]:
            parsed.append(item)
    return parsed


def parse_targets(path: Path) -> list[dict[str, float | str]]:
    fieldnames, rows = targeting_analyzer.load_table(path)
    columns = targeting_analyzer.resolve_columns(fieldnames)
    parsed = []
    for row in rows:
        item: dict[str, float | str] = {
            "campaign": (row.get(columns["campaign"]) or "").strip(),
            "ad_group": (row.get(columns["ad_group"]) or "").strip(),
            "targeting": (row.get(columns["targeting"]) or "").strip(),
            "match_type": (row.get(columns["match_type"]) or "").strip(),
        }
        for metric in ("impressions", "clicks", "spend", "sales", "orders"):
            item[metric] = parse_number(row.get(columns[metric], ""))
        if item["targeting"]:
            parsed.append(item)
    return parsed


def action_for_acos(acos: float | None, has_sales: bool, clicks: float) -> str:
    if not has_sales and clicks >= 10:
        return "negative/exclude candidate after relevance check"
    if acos is None:
        return "monitor"
    if acos >= 0.70:
        return "reduce bid 20-30% or isolate before scaling"
    if acos >= 0.50:
        return "reduce bid 10-20% and monitor next 7 days"
    if acos >= 0.40:
        return "hold or reduce lightly if margin cannot support it"
    if acos <= 0.30:
        return "protect/harvest candidate"
    return "monitor"


def analyze(search_term_path: Path, campaign_path: Path, targeting_path: Path) -> str:
    search_terms = parse_search_terms(search_term_path)
    campaigns = parse_campaigns(campaign_path)
    targets = parse_targets(targeting_path)

    st_totals = {metric: sum(row[metric] for row in search_terms) for metric in ("impressions", "clicks", "spend", "sales", "orders")}
    target_totals = {metric: sum(row[metric] for row in targets) for metric in ("impressions", "clicks", "spend", "sales", "orders")}

    waste_targets = sorted(
        (row for row in targets if row["sales"] == 0 and row["clicks"] >= 5),
        key=lambda row: row["spend"],
        reverse=True,
    )
    high_acos_targets = sorted(
        (row for row in targets if row["sales"] > 0 and (pct(row["spend"], row["sales"]) or 0) > 0.40),
        key=lambda row: pct(row["spend"], row["sales"]) or 0,
        reverse=True,
    )
    protect_terms = sorted(
        (row for row in search_terms if row["orders"] >= 2 and row["sales"] > 0 and (pct(row["spend"], row["sales"]) or 0) <= 0.30),
        key=lambda row: row["sales"],
        reverse=True,
    )
    high_acos_campaigns = sorted(
        (row for row in campaigns if row["sales"] > 0 and (pct(row["spend"], row["sales"]) or 0) > 0.40),
        key=lambda row: pct(row["spend"], row["sales"]) or 0,
        reverse=True,
    )

    lines = [
        "# PPC Action Plan - RUBEX Week 27 2026",
        "",
        "## Sources",
        "",
        f"- Search Term Report: `{search_term_path.name}`",
        f"- Campaign Report: `{campaign_path.name}`",
        f"- Targeting Report: `{targeting_path.name}`",
        "",
        "## Executive summary",
        "",
        f"- Search-term ACOS: {fmt_pct(pct(st_totals['spend'], st_totals['sales']))} on spend {fmt_money(st_totals['spend'])} and sales {fmt_money(st_totals['sales'])}.",
        f"- Targeting-level ACOS: {fmt_pct(pct(target_totals['spend'], target_totals['sales']))} on spend {fmt_money(target_totals['spend'])} and sales {fmt_money(target_totals['sales'])}.",
        "- Primary action area is target-level bid/relevance review, not broad campaign budget changes.",
        "",
        "## Immediate action candidates",
        "",
    ]

    for row in waste_targets[:10]:
        lines.append(
            f"- `{row['targeting']}` ({row['match_type']}) in `{row['campaign']}`: spend {fmt_money(row['spend'])}, clicks {row['clicks']:.0f}, sales {fmt_money(row['sales'])}. Action: {action_for_acos(None, False, row['clicks'])}."
        )

    for row in high_acos_targets[:10]:
        acos = pct(row["spend"], row["sales"])
        lines.append(
            f"- `{row['targeting']}` ({row['match_type']}) in `{row['campaign']}`: ACOS {fmt_pct(acos)}, spend {fmt_money(row['spend'])}, sales {fmt_money(row['sales'])}. Action: {action_for_acos(acos, True, row['clicks'])}."
        )

    lines.extend(["", "## Protect / harvest candidates", ""])
    if protect_terms:
        for row in protect_terms[:10]:
            acos = pct(row["spend"], row["sales"])
            lines.append(
                f"- `{row['search_term']}`: orders {row['orders']:.0f}, ACOS {fmt_pct(acos)}, spend {fmt_money(row['spend'])}, sales {fmt_money(row['sales'])}. Action: exact/isolated harvest candidate after duplicate check."
            )
    else:
        lines.append("- None detected under current rules.")

    lines.extend(["", "## Campaign context", ""])
    if high_acos_campaigns:
        for row in high_acos_campaigns[:10]:
            lines.append(
                f"- `{row['campaign']}`: ACOS {fmt_pct(pct(row['spend'], row['sales']))}, spend {fmt_money(row['spend'])}, sales {fmt_money(row['sales'])}, targeting {row['targeting_type']}."
            )
    else:
        lines.append("- No high-ACOS campaigns detected under current rules.")

    lines.extend([
        "",
        "## Guardrails",
        "",
        "- This is a review plan, not an automatic bulk upload.",
        "- Do not negate converting targets without margin, rank, and campaign-role review.",
        "- Apply bid changes in small batches and measure over the next 7 days.",
        "- Check whether target-level waste is caused by broad/auto leakage before changing campaign budgets.",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    parser.add_argument("--search-term", type=Path)
    parser.add_argument("--campaign", type=Path)
    parser.add_argument("--targeting", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        reports_dir = args.reports_dir.expanduser()
        search_term = args.search_term or latest_matching(reports_dir, ("search_term", "search term"))
        campaign = args.campaign or latest_matching(reports_dir, ("campaign",))
        targeting = args.targeting or latest_matching(reports_dir, ("targeting",))
        report = analyze(search_term.resolve(), campaign.resolve(), targeting.resolve())
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
