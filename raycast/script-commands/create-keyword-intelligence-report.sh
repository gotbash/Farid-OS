#!/bin/bash
# @raycast.schemaVersion 1
# @raycast.title Create Keyword Intelligence Report
# @raycast.mode fullOutput
# @raycast.packageName Farid OS

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ROOT_DIR=$(cd "$SCRIPT_DIR/../.." && pwd)
OUTPUT_PATH=/tmp/farid-os-keyword-intelligence.md
CSV_PATH=/tmp/farid-os-keyword-actions.csv

cd "$ROOT_DIR" || exit 1
PYTHONDONTWRITEBYTECODE=1 python3 tools/warehouse_importer.py >/dev/null || exit $?
PYTHONDONTWRITEBYTECODE=1 python3 tools/product_profile.py import >/dev/null || exit $?
PYTHONDONTWRITEBYTECODE=1 python3 tools/keyword_intelligence.py --output "$OUTPUT_PATH" --csv-output "$CSV_PATH" >/dev/null || exit $?
pbcopy < "$OUTPUT_PATH"
cat "$OUTPUT_PATH"

echo
echo "Keyword intelligence report copied to clipboard."
echo "CSV actions saved to $CSV_PATH"
