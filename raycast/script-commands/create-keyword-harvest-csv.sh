#!/bin/bash
# @raycast.schemaVersion 1
# @raycast.title Create Keyword Harvest CSV
# @raycast.mode fullOutput
# @raycast.packageName Farid OS

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ROOT_DIR=$(cd "$SCRIPT_DIR/../.." && pwd)
CSV_PATH=/tmp/farid-os-keyword-harvest.csv

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
    SELECT keyword, action, match_type, score, reason
    FROM keyword_candidates
    WHERE action IN ('HARVEST_EXACT', 'HARVEST_PHRASE')
    ORDER BY score DESC
    """
).fetchall()
writer = csv.DictWriter(
    __import__("sys").stdout,
    fieldnames=["keyword", "action", "match_type", "score", "reason"],
    lineterminator="\n",
)
writer.writeheader()
for row in rows:
    writer.writerow(dict(row))
PY
pbcopy < "$CSV_PATH"
cat "$CSV_PATH"

echo
echo "Keyword harvest CSV copied to clipboard and saved to $CSV_PATH"
