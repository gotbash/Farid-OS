#!/bin/bash
# @raycast.schemaVersion 1
# @raycast.title Create Competitor Report
# @raycast.mode fullOutput
# @raycast.packageName Farid OS

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ROOT_DIR=$(cd "$SCRIPT_DIR/../.." && pwd)
OUTPUT_PATH=/tmp/farid-os-competitor-report.md

cd "$ROOT_DIR" || exit 1
PYTHONDONTWRITEBYTECODE=1 python3 tools/warehouse_importer.py >/dev/null || exit $?
PYTHONDONTWRITEBYTECODE=1 python3 tools/competitor_tracker.py report --output "$OUTPUT_PATH" || exit $?
pbcopy < "$OUTPUT_PATH"
cat "$OUTPUT_PATH"

echo
echo "Competitor report copied to clipboard and saved to $OUTPUT_PATH"
