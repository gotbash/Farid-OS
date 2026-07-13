#!/usr/bin/env python3
"""Import Rubex Amazon reports into a local SQLite warehouse."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import analyze_latest_rubex_report
import campaign_analyzer
import catalog_performance_analyzer
import search_term_analyzer
import sqp_analyzer
import targeting_analyzer


DEFAULT_REPORTS_DIR = Path("~/Downloads/Rubex/Reports").expanduser()
DEFAULT_DB_PATH = Path("data/farid_os.db")
SCHEMA_VERSION = 1


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_number(value: str) -> float:
    cleaned = "".join(ch for ch in (value or "").replace(",", "") if ch.isdigit() or ch in ".()-")
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


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS warehouse_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS report_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_sha256 TEXT NOT NULL UNIQUE,
            report_type TEXT NOT NULL,
            file_mtime TEXT NOT NULL,
            imported_at TEXT NOT NULL,
            row_count INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'imported',
            error TEXT
        );

        CREATE TABLE IF NOT EXISTS ppc_search_terms (
            report_file_id INTEGER NOT NULL REFERENCES report_files(id) ON DELETE CASCADE,
            search_term TEXT NOT NULL,
            impressions REAL NOT NULL,
            clicks REAL NOT NULL,
            spend REAL NOT NULL,
            sales REAL NOT NULL,
            orders REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ppc_campaigns (
            report_file_id INTEGER NOT NULL REFERENCES report_files(id) ON DELETE CASCADE,
            campaign TEXT NOT NULL,
            status TEXT,
            targeting_type TEXT,
            budget REAL NOT NULL,
            impressions REAL NOT NULL,
            clicks REAL NOT NULL,
            spend REAL NOT NULL,
            sales REAL NOT NULL,
            orders REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ppc_targets (
            report_file_id INTEGER NOT NULL REFERENCES report_files(id) ON DELETE CASCADE,
            campaign TEXT NOT NULL,
            ad_group TEXT,
            targeting TEXT NOT NULL,
            match_type TEXT,
            impressions REAL NOT NULL,
            clicks REAL NOT NULL,
            spend REAL NOT NULL,
            sales REAL NOT NULL,
            orders REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sqp_queries (
            report_file_id INTEGER NOT NULL REFERENCES report_files(id) ON DELETE CASCADE,
            search_query TEXT NOT NULL,
            impressions REAL NOT NULL,
            clicks REAL NOT NULL,
            cart_adds REAL NOT NULL,
            purchases REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS catalog_asins (
            report_file_id INTEGER NOT NULL REFERENCES report_files(id) ON DELETE CASCADE,
            asin TEXT NOT NULL,
            title TEXT,
            impressions REAL NOT NULL,
            clicks REAL NOT NULL,
            cart_adds REAL NOT NULL,
            purchases REAL NOT NULL,
            sales REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS products (
            asin TEXT PRIMARY KEY,
            sku TEXT,
            product_name TEXT,
            brand TEXT DEFAULT 'RUBEX',
            target_acos REAL,
            breakeven_acos REAL,
            unit_margin REAL,
            active INTEGER NOT NULL DEFAULT 1,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS competitors (
            competitor_asin TEXT PRIMARY KEY,
            competitor_name TEXT,
            product_asin TEXT,
            brand TEXT,
            source TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS competitor_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            competitor_asin TEXT NOT NULL,
            captured_at TEXT NOT NULL,
            keyword TEXT,
            search_position INTEGER,
            price REAL,
            rating REAL,
            reviews INTEGER,
            coupon TEXT,
            organic_rank INTEGER,
            sponsored_rank INTEGER,
            raw_source TEXT,
            FOREIGN KEY(competitor_asin) REFERENCES competitors(competitor_asin)
        );

        CREATE TABLE IF NOT EXISTS forecasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            horizon_days INTEGER NOT NULL,
            scenario TEXT NOT NULL,
            spend REAL NOT NULL,
            sales REAL NOT NULL,
            orders REAL NOT NULL,
            acos REAL,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            severity TEXT NOT NULL,
            area TEXT NOT NULL,
            title TEXT NOT NULL,
            detail TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open'
        );

        CREATE VIEW IF NOT EXISTS latest_report_files AS
            SELECT rf.*
            FROM report_files rf
            JOIN (
                SELECT report_type, MAX(imported_at) AS max_imported_at
                FROM report_files
                WHERE status = 'imported'
                GROUP BY report_type
            ) latest
            ON latest.report_type = rf.report_type
            AND latest.max_imported_at = rf.imported_at;

        CREATE INDEX IF NOT EXISTS idx_report_files_type ON report_files(report_type);
        CREATE INDEX IF NOT EXISTS idx_ppc_search_terms_term ON ppc_search_terms(search_term);
        CREATE INDEX IF NOT EXISTS idx_ppc_campaigns_campaign ON ppc_campaigns(campaign);
        CREATE INDEX IF NOT EXISTS idx_ppc_targets_targeting ON ppc_targets(targeting);
        CREATE INDEX IF NOT EXISTS idx_sqp_queries_query ON sqp_queries(search_query);
        CREATE INDEX IF NOT EXISTS idx_catalog_asins_asin ON catalog_asins(asin);
        CREATE INDEX IF NOT EXISTS idx_competitor_snapshots_asin ON competitor_snapshots(competitor_asin);
        CREATE INDEX IF NOT EXISTS idx_forecasts_created_at ON forecasts(created_at);
        CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);
        """
    )
    existing_columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(competitor_snapshots)").fetchall()
    }
    if "keyword" not in existing_columns:
        conn.execute("ALTER TABLE competitor_snapshots ADD COLUMN keyword TEXT")
    if "search_position" not in existing_columns:
        conn.execute("ALTER TABLE competitor_snapshots ADD COLUMN search_position INTEGER")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_competitor_snapshots_keyword ON competitor_snapshots(keyword)")
    conn.execute(
        "INSERT OR REPLACE INTO warehouse_meta(key, value) VALUES (?, ?)",
        ("schema_version", str(SCHEMA_VERSION)),
    )
    conn.commit()


def insert_report_file(conn: sqlite3.Connection, path: Path, report_type: str, file_hash: str) -> int | None:
    existing = conn.execute("SELECT id FROM report_files WHERE file_sha256 = ?", (file_hash,)).fetchone()
    if existing:
        return None
    cursor = conn.execute(
        """
        INSERT INTO report_files(file_name, file_path, file_sha256, report_type, file_mtime, imported_at, row_count)
        VALUES (?, ?, ?, ?, ?, ?, 0)
        """,
        (
            path.name,
            str(path.resolve()),
            file_hash,
            report_type,
            datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).replace(microsecond=0).isoformat(),
            now_iso(),
        ),
    )
    return int(cursor.lastrowid)


def update_report_status(conn: sqlite3.Connection, report_file_id: int, row_count: int, status: str = "imported", error: str | None = None) -> None:
    conn.execute(
        "UPDATE report_files SET row_count = ?, status = ?, error = ? WHERE id = ?",
        (row_count, status, error, report_file_id),
    )


def import_search_terms(conn: sqlite3.Connection, report_file_id: int, path: Path) -> int:
    fieldnames, rows = search_term_analyzer.load_table(path)
    columns = search_term_analyzer.resolve_columns(fieldnames)
    payload = []
    for row in rows:
        search_term = (row.get(columns["search_term"]) or "").strip()
        if not search_term:
            continue
        payload.append(
            (
                report_file_id,
                search_term,
                parse_number(row.get(columns["impressions"], "")),
                parse_number(row.get(columns["clicks"], "")),
                parse_number(row.get(columns["spend"], "")),
                parse_number(row.get(columns["sales"], "")),
                parse_number(row.get(columns["orders"], "")),
            )
        )
    conn.executemany("INSERT INTO ppc_search_terms VALUES (?, ?, ?, ?, ?, ?, ?)", payload)
    return len(payload)


def import_campaigns(conn: sqlite3.Connection, report_file_id: int, path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("Campaign report has no header row")
        columns = campaign_analyzer.resolve_columns(reader.fieldnames)
        rows = list(reader)
    payload = []
    for row in rows:
        campaign = (row.get(columns["campaign"]) or "").strip()
        if not campaign:
            continue
        payload.append(
            (
                report_file_id,
                campaign,
                (row.get(columns["status"]) or "").strip(),
                (row.get(columns["targeting_type"]) or "").strip(),
                parse_number(row.get(columns["budget"], "")),
                parse_number(row.get(columns["impressions"], "")),
                parse_number(row.get(columns["clicks"], "")),
                parse_number(row.get(columns["spend"], "")),
                parse_number(row.get(columns["sales"], "")),
                parse_number(row.get(columns["orders"], "")),
            )
        )
    conn.executemany("INSERT INTO ppc_campaigns VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", payload)
    return len(payload)


def import_targets(conn: sqlite3.Connection, report_file_id: int, path: Path) -> int:
    fieldnames, rows = targeting_analyzer.load_table(path)
    columns = targeting_analyzer.resolve_columns(fieldnames)
    payload = []
    for row in rows:
        targeting = (row.get(columns["targeting"]) or "").strip()
        if not targeting:
            continue
        payload.append(
            (
                report_file_id,
                (row.get(columns["campaign"]) or "").strip(),
                (row.get(columns["ad_group"]) or "").strip(),
                targeting,
                (row.get(columns["match_type"]) or "").strip(),
                parse_number(row.get(columns["impressions"], "")),
                parse_number(row.get(columns["clicks"], "")),
                parse_number(row.get(columns["spend"], "")),
                parse_number(row.get(columns["sales"], "")),
                parse_number(row.get(columns["orders"], "")),
            )
        )
    conn.executemany("INSERT INTO ppc_targets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", payload)
    return len(payload)


def import_sqp(conn: sqlite3.Connection, report_file_id: int, path: Path) -> int:
    parsed, _invalid, _totals, _input_rows = sqp_analyzer.build_report(path)
    payload = [
        (
            report_file_id,
            str(row["search_query"]),
            float(row["impressions"]),
            float(row["clicks"]),
            float(row["cart_adds"]),
            float(row["purchases"]),
        )
        for row in parsed
    ]
    conn.executemany("INSERT INTO sqp_queries VALUES (?, ?, ?, ?, ?, ?)", payload)
    return len(payload)


def import_catalog(conn: sqlite3.Connection, report_file_id: int, path: Path) -> int:
    rows, columns, _header_index = catalog_performance_analyzer.load_rows(path)
    payload = []
    for row in rows:
        asin = (row.get(columns["asin"]) or "").strip()
        if not asin:
            continue
        payload.append(
            (
                report_file_id,
                asin,
                (row.get(columns["title"]) or "").strip(),
                parse_number(row.get(columns["impressions"], "")),
                parse_number(row.get(columns["clicks"], "")),
                parse_number(row.get(columns["cart_adds"], "")),
                parse_number(row.get(columns["purchases"], "")),
                parse_number(row.get(columns["sales"], "")),
            )
        )
    conn.executemany("INSERT INTO catalog_asins VALUES (?, ?, ?, ?, ?, ?, ?, ?)", payload)
    return len(payload)


def import_one(conn: sqlite3.Connection, path: Path) -> tuple[str, int, str]:
    file_hash = sha256_file(path)
    report_type = analyze_latest_rubex_report.detect_report_type(path)
    report_file_id = insert_report_file(conn, path, report_type, file_hash)
    if report_file_id is None:
        return report_type, 0, "skipped_existing"

    try:
        if report_type == "search_term":
            row_count = import_search_terms(conn, report_file_id, path)
        elif report_type == "campaign":
            row_count = import_campaigns(conn, report_file_id, path)
        elif report_type == "targeting":
            row_count = import_targets(conn, report_file_id, path)
        elif report_type == "sqp":
            row_count = import_sqp(conn, report_file_id, path)
        elif report_type == "search_catalog_performance":
            row_count = import_catalog(conn, report_file_id, path)
        else:
            update_report_status(conn, report_file_id, 0, "unsupported", f"Unsupported report type: {report_type}")
            return report_type, 0, "unsupported"
        update_report_status(conn, report_file_id, row_count)
        return report_type, row_count, "imported"
    except Exception as exc:
        update_report_status(conn, report_file_id, 0, "error", str(exc))
        raise


def report_files(reports_dir: Path) -> list[Path]:
    return sorted(
        [
            path
            for path in reports_dir.expanduser().iterdir()
            if path.is_file() and path.suffix.lower() in {".csv", ".xlsx"}
        ],
        key=lambda path: path.stat().st_mtime,
    )


def latest_totals(conn: sqlite3.Connection, table: str, metrics: tuple[str, ...], report_type: str) -> dict[str, float]:
    columns = ", ".join(f"COALESCE(SUM({metric}), 0) AS {metric}" for metric in metrics)
    row = conn.execute(
        f"""
        SELECT {columns}
        FROM {table}
        WHERE report_file_id = (
            SELECT id FROM latest_report_files WHERE report_type = ?
        )
        """,
        (report_type,),
    ).fetchone()
    return {metric: float(row[metric] or 0) for metric in metrics} if row else {metric: 0.0 for metric in metrics}


def build_summary(conn: sqlite3.Connection, imported: list[dict[str, Any]], db_path: Path) -> str:
    reports = conn.execute(
        """
        SELECT report_type, COUNT(*) AS files, SUM(row_count) AS rows
        FROM report_files
        GROUP BY report_type
        ORDER BY report_type
        """
    ).fetchall()
    ppc = latest_totals(conn, "ppc_targets", ("impressions", "clicks", "spend", "sales", "orders"), "targeting")
    sqp = latest_totals(conn, "sqp_queries", ("impressions", "clicks", "cart_adds", "purchases"), "sqp")
    catalog = latest_totals(conn, "catalog_asins", ("impressions", "clicks", "cart_adds", "purchases", "sales"), "search_catalog_performance")
    waste = conn.execute(
        """
        SELECT targeting, match_type, campaign, clicks, spend
        FROM ppc_targets
        WHERE report_file_id = (SELECT id FROM latest_report_files WHERE report_type = 'targeting')
          AND sales = 0
          AND clicks >= 5
        ORDER BY spend DESC
        LIMIT 5
        """
    ).fetchall()
    harvest = conn.execute(
        """
        SELECT search_term, orders, spend, sales
        FROM ppc_search_terms
        WHERE report_file_id = (SELECT id FROM latest_report_files WHERE report_type = 'search_term')
          AND orders >= 2
          AND sales > 0
          AND spend / sales <= 0.30
        ORDER BY sales DESC
        LIMIT 5
        """
    ).fetchall()

    lines = [
        "# Farid OS Data Warehouse Import",
        "",
        f"Database: `{db_path}`",
        "",
        "## Import run",
        "",
    ]
    if imported:
        for item in imported:
            lines.append(f"- `{item['file']}` — {item['report_type']}, {item['status']}, rows {item['rows']}")
    else:
        lines.append("- No supported files found.")
    lines.extend(["", "## Warehouse inventory", ""])
    if reports:
        for row in reports:
            lines.append(f"- {row['report_type']}: {row['files']} files, {row['rows'] or 0} rows")
    else:
        lines.append("- Empty warehouse.")
    lines.extend(
        [
            "",
            "## Latest PPC snapshot",
            "",
            f"- Impressions: {ppc['impressions']:,.0f}",
            f"- Clicks: {ppc['clicks']:,.0f}",
            f"- Spend: {fmt_money(ppc['spend'])}",
            f"- Sales: {fmt_money(ppc['sales'])}",
            f"- Orders: {ppc['orders']:,.0f}",
            f"- CTR: {fmt_pct(pct(ppc['clicks'], ppc['impressions']))}",
            f"- CVR: {fmt_pct(pct(ppc['orders'], ppc['clicks']))}",
            f"- ACOS: {fmt_pct(pct(ppc['spend'], ppc['sales']))}",
            "",
            "## Latest SQP snapshot",
            "",
            f"- Impressions: {sqp['impressions']:,.0f}",
            f"- Clicks: {sqp['clicks']:,.0f}",
            f"- Cart adds: {sqp['cart_adds']:,.0f}",
            f"- Purchases: {sqp['purchases']:,.0f}",
            f"- CTR: {fmt_pct(pct(sqp['clicks'], sqp['impressions']))}",
            f"- Click-to-purchase: {fmt_pct(pct(sqp['purchases'], sqp['clicks']))}",
            "",
            "## Latest Search Catalog snapshot",
            "",
            f"- Impressions: {catalog['impressions']:,.0f}",
            f"- Clicks: {catalog['clicks']:,.0f}",
            f"- Purchases: {catalog['purchases']:,.0f}",
            f"- Search traffic sales: {fmt_money(catalog['sales'])}",
            f"- CTR: {fmt_pct(pct(catalog['clicks'], catalog['impressions']))}",
            "",
            "## PPC action signals from warehouse",
            "",
        ]
    )
    if waste:
        lines.append("### Waste candidates")
        lines.append("")
        for row in waste:
            lines.append(f"- `{row['targeting']}` ({row['match_type']}) in `{row['campaign']}` — clicks {row['clicks']:.0f}, spend {fmt_money(row['spend'])}, zero sales")
        lines.append("")
    if harvest:
        lines.append("### Harvest candidates")
        lines.append("")
        for row in harvest:
            lines.append(f"- `{row['search_term']}` — orders {row['orders']:.0f}, ACOS {fmt_pct(pct(row['spend'], row['sales']))}")
    if not waste and not harvest:
        lines.append("- No immediate PPC action signals under current warehouse rules.")
    lines.extend(
        [
            "",
            "## Next system layer",
            "",
            "- Add weekly snapshots as new report files arrive.",
            "- Add product margin and target ACOS tables before automated bid recommendations.",
            "- Add competitor ASIN snapshots once competitor source is selected.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        db_path = args.db.expanduser()
        if not db_path.is_absolute():
            db_path = Path.cwd() / db_path
        conn = connect(db_path)
        init_schema(conn)
        imported = []
        with conn:
            for path in report_files(args.reports_dir):
                try:
                    report_type, rows, status = import_one(conn, path)
                    imported.append({"file": path.name, "report_type": report_type, "rows": rows, "status": status})
                except ValueError as exc:
                    imported.append({"file": path.name, "report_type": "unknown", "rows": 0, "status": f"error: {exc}"})
        summary = build_summary(conn, imported, db_path)
    except (OSError, sqlite3.Error, csv.Error, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(imported, indent=2, ensure_ascii=False))
        return 0
    if args.output:
        args.output.write_text(summary, encoding="utf-8")
        print(args.output)
    else:
        print(summary, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
