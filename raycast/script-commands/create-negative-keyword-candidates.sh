#!/bin/bash
# @raycast.schemaVersion 1
# @raycast.title Create Negative Keyword Candidates
# @raycast.mode fullOutput
# @raycast.packageName Farid OS

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ROOT_DIR=$(cd "$SCRIPT_DIR/../.." && pwd)
CSV_PATH=/tmp/farid-os-negative-keyword-candidates.csv

cd "$ROOT_DIR" || exit 1
PYTHONDONTWRITEBYTECODE=1 python3 tools/warehouse_importer.py >/dev/null || exit $?
PYTHONDONTWRITEBYTECODE=1 python3 tools/product_profile.py import >/dev/null || exit $?
PYTHONDONTWRITEBYTECODE=1 python3 tools/keyword_intelligence.py --csv-output /tmp/farid-os-keyword-actions-all.csv >/dev/null || exit $?
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY' > "$CSV_PATH"
import csv
import sqlite3

conn = sqlite3.connect("data/farid_os.db")
conn.row_factory = sqlite3.Row
rows = conn.execute(
    """
    SELECT keyword, match_type, score, clicks, spend, sales, orders, reason
    FROM negative_candidates
    ORDER BY spend DESC, clicks DESC
    """
).fetchall()
writer = csv.DictWriter(
    __import__("sys").stdout,
    fieldnames=["keyword", "match_type", "score", "clicks", "spend", "sales", "orders", "reason"],
    lineterminator="\n",
)
writer.writeheader()
for row in rows:
    writer.writerow(dict(row))
PY
pbcopy < "$CSV_PATH"
cat "$CSV_PATH"

echo
echo "Negative keyword candidates copied to clipboard and saved to $CSV_PATH"
