#!/usr/bin/env python3
"""Find and analyze the latest supported Rubex Amazon CSV report."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import catalog_performance_analyzer
import search_term_analyzer
import sqp_analyzer
import top_search_terms_analyzer


DEFAULT_REPORTS_DIR = Path("~/Downloads/Rubex/Reports").expanduser()


def normalize(value: str) -> str:
    return " ".join(value.strip().lower().split())


def latest_csv(reports_dir: Path) -> Path:
    files = [path for path in reports_dir.expanduser().glob("*.csv") if path.is_file()]
    if not files:
        raise ValueError(f"No CSV files found in {reports_dir}")
    return max(files, key=lambda path: path.stat().st_mtime)


def read_header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        first_row = next(reader, None)
        second_row = next(reader, None)
    if first_row is None:
        raise ValueError("CSV has no rows")
    first_cell = normalize(first_row[0]) if first_row else ""
    known_first_columns = {"search query", "asin title", "date", "customer search term", "search term", "search frequency rank"}
    if first_cell not in known_first_columns:
        if second_row and any(normalize(cell) in known_first_columns for cell in second_row):
            return second_row
    return first_row


def detect_report_type(path: Path) -> str:
    header = {normalize(column) for column in read_header(path)}
    if {"search query", "impressions: total count", "clicks: total count", "cart adds: total count", "purchases: total count"}.issubset(header):
        return "sqp"
    if {"asin title", "asin", "impressions: impressions", "clicks: clicks", "cart adds: cart adds", "purchases: purchases"}.issubset(header):
        return "search_catalog_performance"
    if {"search frequency rank", "search term", "top clicked brand #1", "top clicked product #1: asin"}.issubset(header):
        return "top_search_terms"
    if {"customer search term", "impressions", "clicks"}.issubset(header) or {"search term", "impressions", "clicks"}.issubset(header):
        return "search_term"
    if {"date", "customers in awareness", "customers in consideration", "branded search customers", "branded search ratio"}.issubset(header):
        return "brand_analytics_trends"
    raise ValueError("Unsupported CSV schema: " + ", ".join(sorted(header)[:12]))


def analyze(path: Path) -> tuple[str, str]:
    report_type = detect_report_type(path)
    if report_type == "sqp":
        return report_type, sqp_analyzer.wbr_summary(path)
    if report_type == "search_catalog_performance":
        return report_type, catalog_performance_analyzer.analyze(path)
    if report_type == "top_search_terms":
        return report_type, top_search_terms_analyzer.analyze(path, limit=100)
    if report_type == "search_term":
        return report_type, search_term_analyzer.analyze(path, acos_limit=0.40, waste_clicks=8)
    raise ValueError(f"Unsupported report type: {report_type}. Add a dedicated analyzer before using this file.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        path = latest_csv(args.reports_dir)
        report_type, report = analyze(path.resolve())
    except (OSError, ValueError, csv.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    header = f"Detected report type: {report_type}\nSource path: {path.resolve()}\n\n"
    result = header + report
    if args.output:
        args.output.write_text(result, encoding="utf-8")
        print(args.output)
    else:
        print(result, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
