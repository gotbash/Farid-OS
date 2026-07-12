#!/bin/bash
# @raycast.schemaVersion 1
# @raycast.title Analyze Latest Rubex Report
# @raycast.mode fullOutput
# @raycast.packageName Farid OS

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ROOT_DIR=$(cd "$SCRIPT_DIR/../.." && pwd)
OUTPUT_PATH=/tmp/farid-os-latest-rubex-report.md

PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT_DIR/tools/analyze_latest_rubex_report.py" --output "$OUTPUT_PATH" || exit $?
pbcopy < "$OUTPUT_PATH"
cat "$OUTPUT_PATH"

echo
echo "Latest Rubex report analysis copied to clipboard and saved to $OUTPUT_PATH"
