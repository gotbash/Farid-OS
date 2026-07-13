#!/usr/bin/env python3
"""Keyword intelligence and negative mining from the Farid OS warehouse."""

from __future__ import annotations

import argparse
import csv
import re
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import warehouse_importer


DEFAULT_DB_PATH = Path("data/farid_os.db")
DEFAULT_OUTPUT_DIR = Path("/tmp")
STOPWORDS = {"for", "and", "the", "a", "an", "of", "to", "with", "in", "on"}
IRRELEVANT_HINTS = {
    "document",
    "documents",
    "letter",
    "sheet protector",
    "sheet protectors",
    "protector for documents",
    "page protector",
    "page protectors",
    "11 hole",
    "non-glare sheet protector",
}
PRODUCT_HINTS = {"card", "cards", "sleeve", "sleeves", "binder", "trading", "baseball"}


@dataclass
class Candidate:
    keyword: str
    source: str
    action: str
    match_type: str
    score: float
    impressions: float
    clicks: float
    spend: float
    sales: float
    orders: float
    acos: float | None
    cvr: float | None
    reason: str


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def pct(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator else None


def fmt_pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1%}"


def fmt_money(value: float) -> str:
    return f"{value:,.2f}"


def normalize_keyword(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-zA-Z0-9 ]", " ", value.lower())).strip()


def tokens(value: str) -> list[str]:
    return [token for token in normalize_keyword(value).split() if token and token not in STOPWORDS]


def is_long_tail(keyword: str) -> bool:
    return len(tokens(keyword)) >= 4


def relevance_score(keyword: str) -> tuple[float, list[str]]:
    normalized = normalize_keyword(keyword)
    terms = set(tokens(keyword))
    score = 0.0
    reasons = []
    product_matches = terms & PRODUCT_HINTS
    if product_matches:
        score += min(len(product_matches), 3)
        reasons.append("product-term match")
    if "card" in terms and ("sleeve" in terms or "sleeves" in terms):
        score += 3
        reasons.append("core card sleeve intent")
    if "binder" in terms and ("card" in terms or "cards" in terms):
        score += 1
        reasons.append("binder-card intent")
    if any(hint in normalized for hint in IRRELEVANT_HINTS):
        score -= 4
        reasons.append("document/sheet-protector intent risk")
    if is_long_tail(keyword):
        score += 1
        reasons.append("long-tail query")
    return score, reasons


def connect(path: Path) -> sqlite3.Connection:
    db_path = path.expanduser()
    if not db_path.is_absolute():
        db_path = Path.cwd() / db_path
    conn = warehouse_importer.connect(db_path)
    warehouse_importer.init_schema(conn)
    return conn


def latest_search_terms(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT
            search_term AS keyword,
            SUM(impressions) AS impressions,
            SUM(clicks) AS clicks,
            SUM(spend) AS spend,
            SUM(sales) AS sales,
            SUM(orders) AS orders
        FROM ppc_search_terms
        WHERE report_file_id = (SELECT id FROM latest_report_files WHERE report_type = 'search_term')
        GROUP BY search_term
        """
    ).fetchall()


def sqp_lookup(conn: sqlite3.Connection) -> dict[str, sqlite3.Row]:
    return {
        normalize_keyword(row["search_query"]): row
        for row in conn.execute(
            """
            SELECT search_query, impressions, clicks, cart_adds, purchases
            FROM sqp_queries
            WHERE report_file_id = (SELECT id FROM latest_report_files WHERE report_type = 'sqp')
            """
        ).fetchall()
    }


def classify(row: sqlite3.Row, sqp: dict[str, sqlite3.Row], target_acos: float, waste_clicks: int, waste_spend: float) -> Candidate:
    keyword = row["keyword"]
    impressions = float(row["impressions"] or 0)
    clicks = float(row["clicks"] or 0)
    spend = float(row["spend"] or 0)
    sales = float(row["sales"] or 0)
    orders = float(row["orders"] or 0)
    acos = pct(spend, sales)
    cvr = pct(orders, clicks)
    rel_score, rel_reasons = relevance_score(keyword)
    sqp_row = sqp.get(normalize_keyword(keyword))
    sqp_bonus = 0.0
    if sqp_row:
        sqp_bonus += 1
        rel_reasons.append("confirmed in SQP")
        if float(sqp_row["purchases"] or 0) > 0:
            sqp_bonus += 1
            rel_reasons.append("SQP has purchases")

    score = rel_score + sqp_bonus
    action = "MONITOR"
    match_type = ""
    reason_bits = rel_reasons[:]

    if orders >= 2 and sales > 0 and (acos or 99) <= min(target_acos, 0.35) and rel_score > 0:
        action = "HARVEST_EXACT"
        match_type = "exact"
        score += 5
        reason_bits.append(">=2 orders with efficient ACOS")
    elif orders >= 1 and sales > 0 and (acos or 99) <= max(target_acos, 0.45) and rel_score > 0:
        action = "HARVEST_PHRASE"
        match_type = "phrase"
        score += 3
        reason_bits.append("converting relevant query")
    elif sales == 0 and clicks >= waste_clicks and spend >= waste_spend:
        if rel_score <= 0:
            action = "NEGATIVE_PHRASE"
            match_type = "phrase"
            score += 4
            reason_bits.append("zero-sales waste with relevance risk")
        else:
            action = "NEGATIVE_EXACT"
            match_type = "exact"
            score += 2
            reason_bits.append("zero-sales waste; exact negative review")
    elif sales > 0 and (acos or 0) >= 0.50:
        action = "BID_DOWN"
        match_type = "existing"
        score += 1
        reason_bits.append("converting but high ACOS")
    elif rel_score > 0 and (sqp_row or impressions >= 20):
        action = "EXPAND_LISTING_SEO"
        match_type = "seo"
        score += 1
        reason_bits.append("relevant demand signal")

    if is_long_tail(keyword) and action.startswith("HARVEST"):
        score += 1
        reason_bits.append("long-tail harvest priority")

    return Candidate(
        keyword=keyword,
        source="ppc_search_terms+sqp",
        action=action,
        match_type=match_type,
        score=score,
        impressions=impressions,
        clicks=clicks,
        spend=spend,
        sales=sales,
        orders=orders,
        acos=acos,
        cvr=cvr,
        reason=", ".join(dict.fromkeys(reason_bits)) or "rule-based monitor",
    )


def build_candidates(conn: sqlite3.Connection, target_acos: float, waste_clicks: int, waste_spend: float) -> list[Candidate]:
    lookup = sqp_lookup(conn)
    return [
        classify(row, lookup, target_acos, waste_clicks, waste_spend)
        for row in latest_search_terms(conn)
        if normalize_keyword(row["keyword"])
    ]


def save_candidates(conn: sqlite3.Connection, candidates: list[Candidate]) -> None:
    created_at = now_iso()
    conn.execute("DELETE FROM keyword_candidates")
    conn.execute("DELETE FROM negative_candidates")
    conn.execute("DELETE FROM keyword_actions")
    for candidate in candidates:
        if candidate.action != "MONITOR":
            conn.execute(
                """
                INSERT INTO keyword_candidates(
                    created_at, keyword, source, action, match_type, score, impressions, clicks,
                    spend, sales, orders, acos, cvr, reason
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    created_at,
                    candidate.keyword,
                    candidate.source,
                    candidate.action,
                    candidate.match_type,
                    candidate.score,
                    candidate.impressions,
                    candidate.clicks,
                    candidate.spend,
                    candidate.sales,
                    candidate.orders,
                    candidate.acos,
                    candidate.cvr,
                    candidate.reason,
                ),
            )
            conn.execute(
                """
                INSERT INTO keyword_actions(created_at, keyword, action, match_type, campaign, ad_group, status, reason)
                VALUES (?, ?, ?, ?, NULL, NULL, 'review', ?)
                """,
                (created_at, candidate.keyword, candidate.action, candidate.match_type, candidate.reason),
            )
        if candidate.action.startswith("NEGATIVE"):
            conn.execute(
                """
                INSERT INTO negative_candidates(created_at, keyword, source, match_type, score, clicks, spend, sales, orders, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    created_at,
                    candidate.keyword,
                    candidate.source,
                    candidate.match_type,
                    candidate.score,
                    candidate.clicks,
                    candidate.spend,
                    candidate.sales,
                    candidate.orders,
                    candidate.reason,
                ),
            )
    conn.commit()


def section(lines: list[str], title: str, rows: list[Candidate], limit: int = 20) -> None:
    lines.extend(["", f"## {title}", ""])
    if not rows:
        lines.append("- None detected under current rules.")
        return
    for candidate in rows[:limit]:
        lines.append(
            f"- `{candidate.keyword}` — {candidate.action}, score {candidate.score:.1f}, "
            f"orders {candidate.orders:.0f}, ACOS {fmt_pct(candidate.acos)}, "
            f"spend {fmt_money(candidate.spend)}, reason: {candidate.reason}"
        )


def build_report(candidates: list[Candidate]) -> str:
    harvest_exact = sorted([c for c in candidates if c.action == "HARVEST_EXACT"], key=lambda c: c.score, reverse=True)
    harvest_phrase = sorted([c for c in candidates if c.action == "HARVEST_PHRASE"], key=lambda c: c.score, reverse=True)
    long_tail = sorted([c for c in candidates if is_long_tail(c.keyword) and c.action in {"HARVEST_EXACT", "HARVEST_PHRASE", "EXPAND_LISTING_SEO"}], key=lambda c: c.score, reverse=True)
    negatives = sorted([c for c in candidates if c.action.startswith("NEGATIVE")], key=lambda c: (c.spend, c.clicks), reverse=True)
    bid_down = sorted([c for c in candidates if c.action == "BID_DOWN"], key=lambda c: c.acos or 0, reverse=True)
    seo = sorted([c for c in candidates if c.action == "EXPAND_LISTING_SEO"], key=lambda c: c.impressions, reverse=True)
    lines = [
        "# Keyword Intelligence Report",
        "",
        "## Summary",
        "",
        f"- Harvest exact: {len(harvest_exact)}",
        f"- Harvest phrase: {len(harvest_phrase)}",
        f"- Long-tail opportunities: {len(long_tail)}",
        f"- Negative candidates: {len(negatives)}",
        f"- Bid-down candidates: {len(bid_down)}",
        f"- Listing SEO candidates: {len(seo)}",
        "",
        "## Guardrails",
        "",
        "- This is review-ready output, not an automatic bulk upload.",
        "- Confirm campaign role, match type, margin, rank, and inventory before applying negatives or bid changes.",
        "- Auto-target buckets such as `loose-match` should not be treated as literal negative keywords.",
    ]
    section(lines, "Harvest exact", harvest_exact)
    section(lines, "Harvest phrase", harvest_phrase)
    section(lines, "Long-tail opportunities", long_tail)
    section(lines, "Negative candidates", negatives)
    section(lines, "Bid-down candidates", bid_down)
    section(lines, "Listing SEO candidates", seo)
    return "\n".join(lines) + "\n"


def write_csv(path: Path, candidates: list[Candidate]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "keyword",
        "action",
        "match_type",
        "score",
        "impressions",
        "clicks",
        "spend",
        "sales",
        "orders",
        "acos",
        "cvr",
        "reason",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for candidate in candidates:
            if candidate.action == "MONITOR":
                continue
            writer.writerow({field: getattr(candidate, field) for field in fieldnames})
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--target-acos", type=float, default=0.35)
    parser.add_argument("--waste-clicks", type=int, default=2)
    parser.add_argument("--waste-spend", type=float, default=1.0)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--csv-output", type=Path)
    parser.add_argument("--no-save", action="store_true")
    args = parser.parse_args()
    try:
        conn = connect(args.db)
        candidates = build_candidates(conn, args.target_acos, args.waste_clicks, args.waste_spend)
        if not args.no_save:
            save_candidates(conn, candidates)
        report = build_report(candidates)
        if args.csv_output:
            print(write_csv(args.csv_output, candidates))
        if args.output:
            args.output.write_text(report, encoding="utf-8")
            print(args.output)
        elif not args.csv_output:
            print(report, end="")
    except (OSError, sqlite3.Error, ValueError, csv.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
