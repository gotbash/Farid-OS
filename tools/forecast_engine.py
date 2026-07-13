#!/usr/bin/env python3
"""Create a baseline weekly forecast from the local Farid OS warehouse."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_DB_PATH = Path("data/farid_os.db")


def pct(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator else None


def fmt_pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1%}"


def fmt_money(value: float) -> str:
    return f"{value:,.2f}"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def latest_ppc(conn: sqlite3.Connection) -> dict[str, float]:
    row = conn.execute(
        """
        SELECT
            COALESCE(SUM(impressions), 0) AS impressions,
            COALESCE(SUM(clicks), 0) AS clicks,
            COALESCE(SUM(spend), 0) AS spend,
            COALESCE(SUM(sales), 0) AS sales,
            COALESCE(SUM(orders), 0) AS orders
        FROM ppc_targets
        WHERE report_file_id = (
            SELECT id FROM latest_report_files WHERE report_type = 'targeting'
        )
        """
    ).fetchone()
    return {key: float(row[key] or 0) for key in ("impressions", "clicks", "spend", "sales", "orders")}


def latest_catalog(conn: sqlite3.Connection) -> dict[str, float]:
    row = conn.execute(
        """
        SELECT
            COALESCE(SUM(impressions), 0) AS impressions,
            COALESCE(SUM(clicks), 0) AS clicks,
            COALESCE(SUM(purchases), 0) AS purchases,
            COALESCE(SUM(sales), 0) AS sales
        FROM catalog_asins
        WHERE report_file_id = (
            SELECT id FROM latest_report_files WHERE report_type = 'search_catalog_performance'
        )
        """
    ).fetchone()
    return {key: float(row[key] or 0) for key in ("impressions", "clicks", "purchases", "sales")}


def scenario(base: dict[str, float], spend_factor: float, cvr_factor: float, cpc_factor: float) -> dict[str, float]:
    cpc = pct(base["spend"], base["clicks"]) or 0
    cvr = pct(base["orders"], base["clicks"]) or 0
    aov = pct(base["sales"], base["orders"]) or 0
    spend = base["spend"] * spend_factor
    effective_cpc = cpc * cpc_factor if cpc else 0
    clicks = spend / effective_cpc if effective_cpc else 0
    orders = clicks * cvr * cvr_factor
    sales = orders * aov
    return {
        "spend": spend,
        "clicks": clicks,
        "orders": orders,
        "sales": sales,
        "acos": pct(spend, sales) or 0,
    }


def save_forecasts(conn: sqlite3.Connection, forecasts: dict[str, dict[str, float]], horizon_days: int) -> None:
    created_at = now_iso()
    conn.executemany(
        """
        INSERT INTO forecasts(created_at, horizon_days, scenario, spend, sales, orders, acos, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                created_at,
                horizon_days,
                name,
                values["spend"],
                values["sales"],
                values["orders"],
                values["acos"],
                "Baseline scenario from latest PPC targeting report; upgrade to trend model after multiple weekly snapshots.",
            )
            for name, values in forecasts.items()
        ],
    )


def build_report(conn: sqlite3.Connection, horizon_days: int, save: bool) -> str:
    ppc = latest_ppc(conn)
    catalog = latest_catalog(conn)
    if ppc["spend"] == 0 and ppc["sales"] == 0:
        raise ValueError("No PPC targeting data found in warehouse. Run warehouse_importer.py first.")
    forecasts = {
        "low": scenario(ppc, spend_factor=0.90, cvr_factor=0.90, cpc_factor=1.10),
        "base": scenario(ppc, spend_factor=1.00, cvr_factor=1.00, cpc_factor=1.00),
        "high": scenario(ppc, spend_factor=1.15, cvr_factor=1.10, cpc_factor=0.95),
    }
    if save:
        save_forecasts(conn, forecasts, horizon_days)
        conn.commit()

    lines = [
        "# RUBEX Weekly Forecast",
        "",
        f"Horizon: {horizon_days} days",
        "",
        "## Input baseline",
        "",
        f"- PPC spend: {fmt_money(ppc['spend'])}",
        f"- PPC sales: {fmt_money(ppc['sales'])}",
        f"- PPC orders: {ppc['orders']:,.0f}",
        f"- PPC ACOS: {fmt_pct(pct(ppc['spend'], ppc['sales']))}",
        f"- PPC CPC: {fmt_money(pct(ppc['spend'], ppc['clicks']) or 0)}",
        f"- PPC CVR: {fmt_pct(pct(ppc['orders'], ppc['clicks']))}",
        f"- Search Catalog sales: {fmt_money(catalog['sales'])}",
        f"- Search Catalog purchases: {catalog['purchases']:,.0f}",
        "",
        "## Scenarios",
        "",
    ]
    for name, values in forecasts.items():
        lines.extend(
            [
                f"### {name.title()}",
                "",
                f"- Spend: {fmt_money(values['spend'])}",
                f"- Sales: {fmt_money(values['sales'])}",
                f"- Orders: {values['orders']:,.1f}",
                f"- ACOS: {fmt_pct(values['acos'])}",
                "",
            ]
        )
    lines.extend(
        [
            "## Interpretation",
            "",
            "- This is a baseline forecast from the latest available PPC targeting report.",
            "- It is useful for next-week planning, not yet for statistical trend prediction.",
            "- Forecast quality will improve after 4-8 weekly snapshots are loaded into the warehouse.",
            "",
            "## Required next inputs",
            "",
            "- Product margin / break-even ACOS.",
            "- Total Amazon sales for TACoS.",
            "- Inventory position.",
            "- Competitor price/rank snapshots.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--horizon-days", type=int, default=7)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--no-save", action="store_true")
    args = parser.parse_args()
    try:
        db_path = args.db.expanduser()
        if not db_path.is_absolute():
            db_path = Path.cwd() / db_path
        conn = connect(db_path)
        report = build_report(conn, args.horizon_days, save=not args.no_save)
    except (OSError, sqlite3.Error, ValueError) as exc:
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
