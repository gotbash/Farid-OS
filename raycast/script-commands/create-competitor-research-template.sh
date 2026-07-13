#!/bin/bash
# @raycast.schemaVersion 1
# @raycast.title Create Competitor Research Template
# @raycast.mode fullOutput
# @raycast.packageName Farid OS
# @raycast.argument1 { "type": "text", "placeholder": "Keyword", "optional": true }

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ROOT_DIR=$(cd "$SCRIPT_DIR/../.." && pwd)
KEYWORD=${1:-"trading card sleeves"}

cd "$ROOT_DIR" || exit 1
PYTHONDONTWRITEBYTECODE=1 python3 tools/warehouse_importer.py >/dev/null || exit $?
OUTPUT_PATH=$(PYTHONDONTWRITEBYTECODE=1 python3 tools/competitor_tracker.py write-research-template --keyword "$KEYWORD") || exit $?
open -R "$OUTPUT_PATH"
echo "Created competitor research template:"
echo "$OUTPUT_PATH"
echo
echo "Fill the CSV, then run Import Competitor Snapshot and Create Competitor Research Report."
