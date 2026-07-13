#!/usr/bin/env python3
"""Manage competitor ASIN configs, snapshots, and comparison reports."""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import warehouse_importer


DEFAULT_DB_PATH = Path("data/farid_os.db")
DEFAULT_CONFIG_PATH = Path("config/competitors.local.json")
FALLBACK_CONFIG_PATH = Path("config/competitors.example.json")
DEFAULT_SNAPSHOTS_DIR = Path("~/Downloads/Rubex/Competitors").expanduser()
DEFAULT_KEYWORD = "trading card sleeves"
DEFAULT_MARKETPLACE = "US"
DEFAULT_SEARCH_DOMAIN = "amazon.com"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    cleaned = "".join(ch for ch in text.replace(",", "") if ch.isdigit() or ch in ".-")
    return float(cleaned) if cleaned else None


def parse_int(value: Any) -> int | None:
    number = parse_number(value)
    return int(number) if number is not None else None


def db_path(path: Path) -> Path:
    resolved = path.expanduser()
    return resolved if resolved.is_absolute() else Path.cwd() / resolved


def connect(path: Path) -> sqlite3.Connection:
    conn = warehouse_importer.connect(db_path(path))
    warehouse_importer.init_schema(conn)
    return conn


def load_config(path: Path) -> dict[str, Any]:
    config_path = path if path.exists() else FALLBACK_CONFIG_PATH
    return json.loads(config_path.read_text(encoding="utf-8"))


def import_config(conn: sqlite3.Connection, path: Path) -> tuple[int, int]:
    config = load_config(path)
    brand = config.get("brand", "RUBEX")
    products = 0
    competitors = 0
    for product in config.get("products", []):
        asin = str(product.get("asin", "")).strip()
        if not asin:
            continue
        conn.execute(
            """
            INSERT INTO products(asin, sku, product_name, brand, target_acos, breakeven_acos, unit_margin, active, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
            ON CONFLICT(asin) DO UPDATE SET
                sku = excluded.sku,
                product_name = excluded.product_name,
                brand = excluded.brand,
                target_acos = excluded.target_acos,
                breakeven_acos = excluded.breakeven_acos,
                unit_margin = excluded.unit_margin,
                active = excluded.active,
                notes = excluded.notes
            """,
            (
                asin,
                product.get("sku"),
                product.get("product_name"),
                product.get("brand", brand),
                product.get("target_acos"),
                product.get("breakeven_acos"),
                product.get("unit_margin"),
                product.get("notes"),
            ),
        )
        products += 1
        for competitor in product.get("competitors", []):
            competitor_asin = str(competitor.get("competitor_asin", "")).strip()
            if not competitor_asin or competitor_asin == "REPLACE_WITH_COMPETITOR_ASIN":
                continue
            conn.execute(
                """
                INSERT INTO competitors(competitor_asin, competitor_name, product_asin, brand, source, active, notes)
                VALUES (?, ?, ?, ?, ?, 1, ?)
                ON CONFLICT(competitor_asin) DO UPDATE SET
                    competitor_name = excluded.competitor_name,
                    product_asin = excluded.product_asin,
                    brand = excluded.brand,
                    source = excluded.source,
                    active = excluded.active,
                    notes = excluded.notes
                """,
                (
                    competitor_asin,
                    competitor.get("competitor_name"),
                    asin,
                    competitor.get("brand"),
                    competitor.get("source", "manual"),
                    competitor.get("notes"),
                ),
            )
            competitors += 1
    conn.commit()
    return products, competitors


def latest_snapshot_file(directory: Path) -> Path:
    files = sorted(
        [path for path in directory.expanduser().iterdir() if path.is_file() and path.suffix.lower() == ".csv"],
        key=lambda path: path.stat().st_mtime,
    )
    if not files:
        raise ValueError(f"No competitor snapshot CSV files found in {directory}")
    return files[-1]


def import_snapshot(conn: sqlite3.Connection, path: Path) -> int:
    with path.expanduser().open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("Snapshot CSV has no header row")
        rows = list(reader)
    inserted = 0
    captured_at_default = now_iso()
    for row in rows:
        asin = (row.get("competitor_asin") or row.get("asin") or "").strip()
        if not asin:
            continue
        existing = conn.execute("SELECT 1 FROM competitors WHERE competitor_asin = ?", (asin,)).fetchone()
        if not existing:
            conn.execute(
                """
                INSERT INTO competitors(competitor_asin, competitor_name, product_asin, brand, source, active, notes)
                VALUES (?, ?, ?, ?, 'snapshot_csv', 1, ?)
                """,
                (
                    asin,
                    row.get("competitor_name") or row.get("title"),
                    row.get("product_asin"),
                    row.get("brand"),
                    "Created automatically from competitor snapshot CSV.",
                ),
            )
        conn.execute(
            """
            INSERT INTO competitor_snapshots(
                competitor_asin, captured_at, marketplace, search_domain, search_url, keyword, search_position, price, rating, reviews, coupon,
                organic_rank, sponsored_rank, raw_source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                asin,
                row.get("captured_at") or captured_at_default,
                row.get("marketplace") or DEFAULT_MARKETPLACE,
                row.get("search_domain") or DEFAULT_SEARCH_DOMAIN,
                row.get("search_url") or (amazon_search_url(row.get("keyword", "")) if row.get("keyword") else None),
                row.get("keyword"),
                parse_int(row.get("search_position")),
                parse_number(row.get("price")),
                parse_number(row.get("rating")),
                parse_int(row.get("reviews")),
                row.get("coupon"),
                parse_int(row.get("organic_rank")),
                parse_int(row.get("sponsored_rank")),
                row.get("raw_source") or path.name,
            ),
        )
        inserted += 1
    conn.commit()
    return inserted


def competitor_rows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        WITH ranked AS (
            SELECT
                c.competitor_asin,
                c.competitor_name,
                c.product_asin,
                c.brand,
                s.captured_at,
                s.marketplace,
                s.search_domain,
                s.search_url,
                s.keyword,
                s.search_position,
                s.price,
                s.rating,
                s.reviews,
                s.coupon,
                s.organic_rank,
                s.sponsored_rank,
                ROW_NUMBER() OVER (PARTITION BY c.competitor_asin ORDER BY s.captured_at DESC, s.id DESC) AS rn,
                LAG(s.price) OVER (PARTITION BY c.competitor_asin ORDER BY s.captured_at, s.id) AS prev_price,
                LAG(s.rating) OVER (PARTITION BY c.competitor_asin ORDER BY s.captured_at, s.id) AS prev_rating,
                LAG(s.reviews) OVER (PARTITION BY c.competitor_asin ORDER BY s.captured_at, s.id) AS prev_reviews,
                LAG(s.organic_rank) OVER (PARTITION BY c.competitor_asin ORDER BY s.captured_at, s.id) AS prev_organic_rank,
                LAG(s.sponsored_rank) OVER (PARTITION BY c.competitor_asin ORDER BY s.captured_at, s.id) AS prev_sponsored_rank
            FROM competitors c
            LEFT JOIN competitor_snapshots s ON s.competitor_asin = c.competitor_asin
            WHERE c.active = 1
        )
        SELECT * FROM ranked WHERE rn = 1 ORDER BY product_asin, competitor_asin
        """
    ).fetchall()


def delta(current: Any, previous: Any, suffix: str = "") -> str:
    if current is None:
        return "n/a"
    if previous is None:
        return f"{current}{suffix}"
    change = current - previous
    sign = "+" if change > 0 else ""
    return f"{current}{suffix} ({sign}{change:g})"


def money_delta(current: Any, previous: Any) -> str:
    if current is None:
        return "n/a"
    if previous is None:
        return f"{current:,.2f}"
    change = current - previous
    sign = "+" if change > 0 else ""
    return f"{current:,.2f} ({sign}{change:,.2f})"


def build_report(conn: sqlite3.Connection) -> str:
    rows = competitor_rows(conn)
    products = conn.execute("SELECT COUNT(*) AS count FROM products WHERE active = 1").fetchone()["count"]
    competitors = conn.execute("SELECT COUNT(*) AS count FROM competitors WHERE active = 1").fetchone()["count"]
    snapshots = conn.execute("SELECT COUNT(*) AS count FROM competitor_snapshots").fetchone()["count"]
    lines = [
        "# Competitor Tracker Report",
        "",
        "## Coverage",
        "",
        f"- Active products: {products}",
        f"- Active competitors: {competitors}",
        f"- Snapshots: {snapshots}",
        "",
        "## Latest competitor snapshot",
        "",
    ]
    if not rows:
        lines.extend(
            [
                "- No competitors configured yet.",
                "",
                "## Next step",
                "",
                "- Copy `config/competitors.example.json` to `config/competitors.local.json` and replace competitor ASINs.",
                "- Or import a CSV snapshot with columns: competitor_asin, competitor_name, product_asin, brand, price, rating, reviews, coupon, organic_rank, sponsored_rank.",
            ]
        )
        return "\n".join(lines) + "\n"
    for row in rows:
        lines.extend(
            [
                f"### {row['competitor_asin']} — {row['competitor_name'] or 'Unnamed competitor'}",
                "",
                f"- Product ASIN: `{row['product_asin'] or 'n/a'}`",
                f"- Brand: {row['brand'] or 'n/a'}",
                f"- Captured at: {row['captured_at'] or 'no snapshot yet'}",
                f"- Marketplace: {row['marketplace'] or DEFAULT_MARKETPLACE}",
                f"- Search domain: {row['search_domain'] or DEFAULT_SEARCH_DOMAIN}",
                f"- Keyword: {row['keyword'] or 'n/a'}",
                f"- Search position: {row['search_position'] or 'n/a'}",
                f"- Price: {money_delta(row['price'], row['prev_price'])}",
                f"- Rating: {delta(row['rating'], row['prev_rating'])}",
                f"- Reviews: {delta(row['reviews'], row['prev_reviews'])}",
                f"- Coupon: {row['coupon'] or 'n/a'}",
                f"- Organic rank: {delta(row['organic_rank'], row['prev_organic_rank'])}",
                f"- Sponsored rank: {delta(row['sponsored_rank'], row['prev_sponsored_rank'])}",
                "",
            ]
        )
    lines.extend(
        [
            "## Operating use",
            "",
            "- Use price drops, review acceleration, coupon changes, and rank movement as weekly alert inputs.",
            "- Compare competitor movement with PPC ACOS, CTR, CVR, and Search Catalog conversion before changing bids.",
            "- Treat missing snapshot fields as unknown, not as zero.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_sample_snapshot(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "competitor_asin": "REPLACE_WITH_COMPETITOR_ASIN",
            "competitor_name": "Competitor product name",
            "product_asin": "B07VRTQJL8",
            "brand": "Competitor brand",
            "marketplace": DEFAULT_MARKETPLACE,
            "search_domain": DEFAULT_SEARCH_DOMAIN,
            "search_url": amazon_search_url(DEFAULT_KEYWORD),
            "keyword": DEFAULT_KEYWORD,
            "search_position": "1",
            "price": "12.99",
            "rating": "4.6",
            "reviews": "1234",
            "coupon": "10% off",
            "organic_rank": "3",
            "sponsored_rank": "1",
            "captured_at": now_iso(),
            "raw_source": "manual",
        }
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return path


def slugify(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    return "-".join(part for part in slug.split("-") if part)


def amazon_search_url(keyword: str, domain: str = DEFAULT_SEARCH_DOMAIN) -> str:
    query = "+".join(keyword.strip().split())
    return f"https://www.{domain}/s?k={query}"


def write_research_template(path: Path, keyword: str, product_asin: str, rows: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "keyword",
        "search_position",
        "competitor_asin",
        "competitor_name",
        "product_asin",
        "brand",
        "marketplace",
        "search_domain",
        "search_url",
        "price",
        "rating",
        "reviews",
        "coupon",
        "organic_rank",
        "sponsored_rank",
        "captured_at",
        "raw_source",
    ]
    captured_at = now_iso()
    payload = [
        {
            "keyword": keyword,
            "search_position": i,
            "competitor_asin": "",
            "competitor_name": "",
            "product_asin": product_asin,
            "brand": "",
            "marketplace": DEFAULT_MARKETPLACE,
            "search_domain": DEFAULT_SEARCH_DOMAIN,
            "search_url": amazon_search_url(keyword),
            "price": "",
            "rating": "",
            "reviews": "",
            "coupon": "",
            "organic_rank": "",
            "sponsored_rank": "",
            "captured_at": captured_at,
            "raw_source": "manual amazon search",
        }
        for i in range(1, rows + 1)
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(payload)
    return path


def threat_level(row: sqlite3.Row) -> tuple[int, str]:
    score = 0
    reasons = []
    if row["price"] is not None and row["own_avg_price"] is not None and row["price"] < row["own_avg_price"]:
        score += 2
        reasons.append("price below catalog ASP")
    if row["reviews"] is not None and row["reviews"] >= 1000:
        score += 2
        reasons.append("large review moat")
    if row["rating"] is not None and row["rating"] >= 4.5:
        score += 1
        reasons.append("strong rating")
    if row["coupon"]:
        score += 1
        reasons.append("coupon active")
    if row["organic_rank"] is not None and row["organic_rank"] <= 5:
        score += 2
        reasons.append("top organic position")
    if row["sponsored_rank"] is not None and row["sponsored_rank"] <= 3:
        score += 1
        reasons.append("paid visibility")
    if score >= 6:
        level = "High"
    elif score >= 3:
        level = "Medium"
    else:
        level = "Low"
    return score, f"{level} — " + (", ".join(reasons) if reasons else "limited observable threat")


def research_rows(conn: sqlite3.Connection, keyword: str | None = None) -> list[sqlite3.Row]:
    where = "WHERE s.keyword = ?" if keyword else ""
    params = (keyword,) if keyword else ()
    return conn.execute(
        f"""
        WITH latest AS (
            SELECT
                c.competitor_asin,
                c.competitor_name,
                c.product_asin,
                c.brand,
                s.marketplace,
                s.search_domain,
                s.search_url,
                s.keyword,
                s.search_position,
                s.captured_at,
                s.price,
                s.rating,
                s.reviews,
                s.coupon,
                s.organic_rank,
                s.sponsored_rank,
                ROW_NUMBER() OVER (
                    PARTITION BY c.competitor_asin, COALESCE(s.keyword, '')
                    ORDER BY s.captured_at DESC, s.id DESC
                ) AS rn
            FROM competitors c
            JOIN competitor_snapshots s ON s.competitor_asin = c.competitor_asin
            {where}
        ),
        own AS (
            SELECT AVG(sales / NULLIF(purchases, 0)) AS own_avg_price
            FROM catalog_asins
            WHERE purchases > 0
        )
        SELECT latest.*, own.own_avg_price
        FROM latest
        CROSS JOIN own
        WHERE latest.rn = 1
        ORDER BY keyword, COALESCE(organic_rank, 999), COALESCE(search_position, 999), competitor_asin
        """,
        params,
    ).fetchall()


def build_research_report(conn: sqlite3.Connection, keyword: str | None = None) -> str:
    rows = research_rows(conn, keyword)
    title_keyword = keyword or "all tracked keywords"
    lines = [
        f"# Competitor Research Report — {title_keyword}",
        "",
        "## Coverage",
        "",
        f"- Competitor rows: {len(rows)}",
        f"- Keyword filter: {keyword or 'all'}",
        "",
    ]
    if not rows:
        lines.extend(
            [
                "## Missing input",
                "",
                "- No competitor snapshots found for this keyword.",
                "- Run `Create Competitor Research Template`, fill the CSV, then run `Import Competitor Snapshot`.",
            ]
        )
        return "\n".join(lines) + "\n"

    high = []
    medium = []
    low = []
    for row in rows:
        score, level_text = threat_level(row)
        item = (score, level_text, row)
        if level_text.startswith("High"):
            high.append(item)
        elif level_text.startswith("Medium"):
            medium.append(item)
        else:
            low.append(item)

    lines.extend(["## Threat summary", ""])
    lines.append(f"- High threat competitors: {len(high)}")
    lines.append(f"- Medium threat competitors: {len(medium)}")
    lines.append(f"- Low threat competitors: {len(low)}")
    lines.extend(["", "## Competitor map", ""])
    for score, level_text, row in sorted(high + medium + low, key=lambda item: item[0], reverse=True):
        lines.extend(
            [
                f"### {row['competitor_asin']} — {row['competitor_name'] or 'Unnamed competitor'}",
                "",
                f"- Threat: {level_text}",
                f"- Marketplace: {row['marketplace'] or DEFAULT_MARKETPLACE}",
                f"- Search domain: {row['search_domain'] or DEFAULT_SEARCH_DOMAIN}",
                f"- Search URL: {row['search_url'] or 'n/a'}",
                f"- Keyword: {row['keyword'] or 'n/a'}",
                f"- Product ASIN: `{row['product_asin'] or 'n/a'}`",
                f"- Price: {money_delta(row['price'], None)}",
                f"- Rating / reviews: {row['rating'] or 'n/a'} / {row['reviews'] or 'n/a'}",
                f"- Coupon: {row['coupon'] or 'n/a'}",
                f"- Organic rank: {row['organic_rank'] or 'n/a'}",
                f"- Sponsored rank: {row['sponsored_rank'] or 'n/a'}",
                "",
            ]
        )
    lines.extend(
        [
            "## Recommended actions",
            "",
            "- If high-threat competitors are cheaper with strong reviews, check offer gap before increasing bids.",
            "- If competitors dominate organic rank but paid rank is weak, test Sponsored Products defense/conquesting carefully.",
            "- If competitors use coupons, compare RUBEX CTR/CVR before deciding whether to match promo pressure.",
            "- If RUBEX has strong CVR but weak CTR, prioritize image/title/offer testing over broad bid increases.",
            "",
            "## Next data needed",
            "",
            "- RUBEX own live price and coupon status.",
            "- Inventory position.",
            "- Margin / break-even ACOS.",
            "- Repeat snapshot next week for movement detection.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    subparsers = parser.add_subparsers(dest="command", required=True)

    config_parser = subparsers.add_parser("import-config")
    config_parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)

    snapshot_parser = subparsers.add_parser("import-snapshot")
    snapshot_parser.add_argument("--snapshot", type=Path)
    snapshot_parser.add_argument("--snapshots-dir", type=Path, default=DEFAULT_SNAPSHOTS_DIR)

    report_parser = subparsers.add_parser("report")
    report_parser.add_argument("--output", type=Path)

    research_template_parser = subparsers.add_parser("write-research-template")
    research_template_parser.add_argument("--keyword", default=DEFAULT_KEYWORD)
    research_template_parser.add_argument("--product-asin", default="B07VRTQJL8")
    research_template_parser.add_argument("--rows", type=int, default=10)
    research_template_parser.add_argument("--output", type=Path)

    research_report_parser = subparsers.add_parser("research-report")
    research_report_parser.add_argument("--keyword")
    research_report_parser.add_argument("--output", type=Path)

    sample_parser = subparsers.add_parser("write-sample-snapshot")
    sample_parser.add_argument("--output", type=Path, default=Path("examples/competitor-snapshot-sample.csv"))

    args = parser.parse_args()
    try:
        conn = connect(args.db)
        if args.command == "import-config":
            products, competitors = import_config(conn, args.config)
            print(f"Imported products: {products}")
            print(f"Imported competitors: {competitors}")
        elif args.command == "import-snapshot":
            snapshot = args.snapshot or latest_snapshot_file(args.snapshots_dir)
            inserted = import_snapshot(conn, snapshot)
            print(f"Imported competitor snapshots: {inserted}")
            print(f"Source: {snapshot}")
        elif args.command == "report":
            report = build_report(conn)
            if args.output:
                args.output.write_text(report, encoding="utf-8")
                print(args.output)
            else:
                print(report, end="")
        elif args.command == "write-research-template":
            output = args.output or Path("~/Downloads/Rubex/Competitors").expanduser() / f"competitor_research_{slugify(args.keyword)}.csv"
            print(write_research_template(output, args.keyword, args.product_asin, args.rows))
        elif args.command == "research-report":
            report = build_research_report(conn, args.keyword)
            if args.output:
                args.output.write_text(report, encoding="utf-8")
                print(args.output)
            else:
                print(report, end="")
        elif args.command == "write-sample-snapshot":
            print(write_sample_snapshot(args.output))
    except (OSError, sqlite3.Error, ValueError, json.JSONDecodeError, csv.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
