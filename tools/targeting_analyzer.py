#!/usr/bin/env python3
"""Analyze Amazon Sponsored Products Targeting reports."""

from __future__ import annotations

import argparse
import csv
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile


ALIASES = {
    "campaign": {"campaign name"},
    "ad_group": {"ad group name"},
    "targeting": {"targeting"},
    "match_type": {"match type"},
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


def cell_text(cell: ET.Element, shared_strings: list[str], namespace: dict[str, str]) -> str:
    cell_type = cell.get("t")
    if cell_type == "inlineStr":
        return "".join(text.text or "" for text in cell.findall(".//a:t", namespace))
    value = cell.find("a:v", namespace)
    if value is None or value.text is None:
        return ""
    if cell_type == "s":
        return shared_strings[int(value.text)]
    return value.text


def load_xlsx(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    namespace = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with ZipFile(path) as archive:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in root.findall("a:si", namespace):
                shared_strings.append("".join(text.text or "" for text in item.findall(".//a:t", namespace)))
        root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        sheet_rows = root.findall(".//a:sheetData/a:row", namespace)
        if not sheet_rows:
            raise ValueError("XLSX contains no rows")
        fieldnames = [cell_text(cell, shared_strings, namespace).strip() for cell in sheet_rows[0].findall("a:c", namespace)]
        rows = []
        for row in sheet_rows[1:]:
            values = [cell_text(cell, shared_strings, namespace) for cell in row.findall("a:c", namespace)]
            rows.append(dict(zip(fieldnames, values)))
    return fieldnames, rows


def load_table(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if path.suffix.lower() == ".xlsx":
        return load_xlsx(path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV has no header row")
        return reader.fieldnames, list(reader)


def analyze(path: Path, acos_limit: float = 0.40, waste_clicks: int = 5) -> str:
    fieldnames, rows = load_table(path)
    columns = resolve_columns(fieldnames)
    if not rows:
        raise ValueError("Report contains no data rows")

    parsed = []
    invalid = []
    for line_number, row in enumerate(rows, start=2):
        try:
            item = {
                "campaign": (row.get(columns["campaign"]) or "").strip(),
                "ad_group": (row.get(columns["ad_group"]) or "").strip(),
                "targeting": (row.get(columns["targeting"]) or "").strip(),
                "match_type": (row.get(columns["match_type"]) or "").strip(),
            }
            for metric in ("impressions", "clicks", "spend", "sales", "orders"):
                item[metric] = parse_number(row.get(columns[metric], ""))
            if not item["targeting"]:
                raise ValueError("empty targeting")
            if item["clicks"] > item["impressions"]:
                raise ValueError("clicks exceed impressions")
            parsed.append(item)
        except ValueError as exc:
            invalid.append((line_number, str(exc)))

    totals = {metric: sum(row[metric] for row in parsed) for metric in ("impressions", "clicks", "spend", "sales", "orders")}
    waste = sorted(
        (row for row in parsed if row["sales"] == 0 and row["clicks"] >= waste_clicks),
        key=lambda row: row["spend"],
        reverse=True,
    )
    high_acos = sorted(
        (row for row in parsed if row["sales"] > 0 and (pct(row["spend"], row["sales"]) or 0) > acos_limit),
        key=lambda row: pct(row["spend"], row["sales"]) or 0,
        reverse=True,
    )
    harvest = sorted(
        (row for row in parsed if row["orders"] >= 1 and row["sales"] > 0 and (pct(row["spend"], row["sales"]) or 0) <= 0.30),
        key=lambda row: row["sales"],
        reverse=True,
    )

    lines = [
        "# Sponsored Products Targeting Report Analysis",
        "",
        f"Source: `{path.name}`",
        "",
        "## Data quality",
        "",
        f"- Input rows: {len(rows)}",
        f"- Valid rows: {len(parsed)}",
        f"- Invalid rows excluded: {len(invalid)}",
        "",
        "## Targeting summary",
        "",
        f"- Targets: {len(parsed):,}",
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
        f"## Waste candidates - >={waste_clicks} clicks and zero attributed sales",
        "",
    ]
    if waste:
        lines.extend(
            f"- `{row['targeting']}` ({row['match_type']}) - spend {fmt_money(row['spend'])}, clicks {row['clicks']:.0f}, campaign `{row['campaign']}`"
            for row in waste[:20]
        )
    else:
        lines.append("- None detected under the configured rule.")
    lines.extend(["", f"## High-ACOS targets above {acos_limit:.0%}", ""])
    if high_acos:
        lines.extend(
            f"- `{row['targeting']}` ({row['match_type']}) - ACOS {fmt_pct(pct(row['spend'], row['sales']))}, spend {fmt_money(row['spend'])}, sales {fmt_money(row['sales'])}, campaign `{row['campaign']}`"
            for row in high_acos[:20]
        )
    else:
        lines.append("- None detected.")
    lines.extend(["", "## Harvest / protect candidates", ""])
    if harvest:
        lines.extend(
            f"- `{row['targeting']}` ({row['match_type']}) - ACOS {fmt_pct(pct(row['spend'], row['sales']))}, orders {row['orders']:.0f}, campaign `{row['campaign']}`"
            for row in harvest[:20]
        )
    else:
        lines.append("- None detected under the current rule.")
    lines.extend([
        "",
        "## Recommended actions",
        "",
        "- Review high-ACOS targets before changing campaign-level budgets.",
        "- Protect harvest candidates with controlled bids and exact/isolated structure where appropriate.",
        "- Do not negate converting targets without checking margin, rank, and campaign role.",
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
    parser.add_argument("--waste-clicks", type=int, default=5)
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
