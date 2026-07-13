#!/usr/bin/env python3
"""Import and inspect product intent profiles for Farid OS."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

import warehouse_importer


DEFAULT_DB_PATH = Path("data/farid_os.db")
DEFAULT_PROFILE_PATH = Path("config/product-profiles.local.json")
FALLBACK_PROFILE_PATH = Path("config/product-profiles.example.json")


def db_path(path: Path) -> Path:
    resolved = path.expanduser()
    return resolved if resolved.is_absolute() else Path.cwd() / resolved


def connect(path: Path) -> sqlite3.Connection:
    conn = warehouse_importer.connect(db_path(path))
    warehouse_importer.init_schema(conn)
    return conn


def load_profiles(path: Path) -> list[dict[str, Any]]:
    profile_path = path if path.exists() else FALLBACK_PROFILE_PATH
    payload = json.loads(profile_path.read_text(encoding="utf-8"))
    return payload.get("profiles", [])


def as_json(value: Any) -> str:
    return json.dumps(value or [], ensure_ascii=False)


def import_profiles(conn: sqlite3.Connection, path: Path) -> int:
    profiles = load_profiles(path)
    imported = 0
    for profile in profiles:
        asin = str(profile.get("asin", "")).strip()
        product_name = str(profile.get("product_name", "")).strip()
        if not asin or not product_name:
            continue
        conn.execute(
            """
            INSERT INTO product_profiles(
                asin, sku, product_name, brand, target_customer, core_terms, must_include,
                optional_terms, irrelevant_terms, negative_intent_terms, target_acos,
                breakeven_acos, notes, active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(asin) DO UPDATE SET
                sku = excluded.sku,
                product_name = excluded.product_name,
                brand = excluded.brand,
                target_customer = excluded.target_customer,
                core_terms = excluded.core_terms,
                must_include = excluded.must_include,
                optional_terms = excluded.optional_terms,
                irrelevant_terms = excluded.irrelevant_terms,
                negative_intent_terms = excluded.negative_intent_terms,
                target_acos = excluded.target_acos,
                breakeven_acos = excluded.breakeven_acos,
                notes = excluded.notes,
                active = excluded.active
            """,
            (
                asin,
                profile.get("sku"),
                product_name,
                profile.get("brand", "RUBEX"),
                profile.get("target_customer"),
                as_json(profile.get("core_terms")),
                as_json(profile.get("must_include")),
                as_json(profile.get("optional_terms")),
                as_json(profile.get("irrelevant_terms")),
                as_json(profile.get("negative_intent_terms")),
                profile.get("target_acos"),
                profile.get("breakeven_acos"),
                profile.get("notes"),
            ),
        )
        conn.execute(
            """
            INSERT INTO products(asin, sku, product_name, brand, target_acos, breakeven_acos, notes, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(asin) DO UPDATE SET
                sku = excluded.sku,
                product_name = excluded.product_name,
                brand = excluded.brand,
                target_acos = excluded.target_acos,
                breakeven_acos = excluded.breakeven_acos,
                notes = excluded.notes,
                active = excluded.active
            """,
            (
                asin,
                profile.get("sku"),
                product_name,
                profile.get("brand", "RUBEX"),
                profile.get("target_acos"),
                profile.get("breakeven_acos"),
                profile.get("notes"),
            ),
        )
        imported += 1
    conn.commit()
    return imported


def active_profiles(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM product_profiles WHERE active = 1 ORDER BY product_name").fetchall()


def build_report(conn: sqlite3.Connection) -> str:
    rows = active_profiles(conn)
    lines = ["# Product Profiles", "", f"- Active profiles: {len(rows)}", ""]
    if not rows:
        lines.extend([
            "No product profiles loaded.",
            "",
            "Run `Import Product Profiles` or create `config/product-profiles.local.json`.",
        ])
        return "\n".join(lines) + "\n"
    for row in rows:
        lines.extend(
            [
                f"## {row['product_name']}",
                "",
                f"- ASIN: `{row['asin']}`",
                f"- Brand: {row['brand']}",
                f"- Target ACOS: {row['target_acos'] if row['target_acos'] is not None else 'n/a'}",
                f"- Core terms: {', '.join(json.loads(row['core_terms']))}",
                f"- Must include: {', '.join(json.loads(row['must_include']))}",
                f"- Optional terms: {', '.join(json.loads(row['optional_terms']))}",
                f"- Irrelevant terms: {', '.join(json.loads(row['irrelevant_terms']))}",
                f"- Target customer: {row['target_customer'] or 'n/a'}",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    subparsers = parser.add_subparsers(dest="command", required=True)
    import_parser = subparsers.add_parser("import")
    import_parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE_PATH)
    report_parser = subparsers.add_parser("report")
    report_parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        conn = connect(args.db)
        if args.command == "import":
            imported = import_profiles(conn, args.profile)
            print(f"Imported product profiles: {imported}")
        elif args.command == "report":
            report = build_report(conn)
            if args.output:
                args.output.write_text(report, encoding="utf-8")
                print(args.output)
            else:
                print(report, end="")
    except (OSError, sqlite3.Error, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
