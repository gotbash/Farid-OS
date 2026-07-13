#!/bin/bash
# @raycast.schemaVersion 1
# @raycast.title Create Competitor Research Report
# @raycast.mode fullOutput
# @raycast.packageName Farid OS
# @raycast.argument1 { "type": "text", "placeholder": "Keyword", "optional": true }

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ROOT_DIR=$(cd "$SCRIPT_DIR/../.." && pwd)
KEYWORD=${1:-}
OUTPUT_PATH=/tmp/farid-os-competitor-research-report.md

cd "$ROOT_DIR" || exit 1
PYTHONDONTWRITEBYTECODE=1 python3 tools/warehouse_importer.py >/dev/null || exit $?
if [ -n "$KEYWORD" ]; then
  PYTHONDONTWRITEBYTECODE=1 python3 tools/competitor_tracker.py research-report --keyword "$KEYWORD" --output "$OUTPUT_PATH" || exit $?
else
  PYTHONDONTWRITEBYTECODE=1 python3 tools/competitor_tracker.py research-report --output "$OUTPUT_PATH" || exit $?
fi
pbcopy < "$OUTPUT_PATH"
cat "$OUTPUT_PATH"

echo
echo "Competitor research report copied to clipboard and saved to $OUTPUT_PATH"
