#!/bin/bash
# Required parameters: 1
# @raycast.schemaVersion 1
# @raycast.title Prepare SQP WBR Summary
# @raycast.mode fullOutput
# @raycast.packageName Farid OS
# @raycast.argument1 { "type": "text", "placeholder": "Absolute path to SQP CSV" }

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ROOT_DIR=$(cd "$SCRIPT_DIR/../.." && pwd)
OUTPUT_PATH=/tmp/farid-os-sqp-wbr-summary.md

python3 "$ROOT_DIR/tools/sqp_analyzer.py" "$1" --wbr --output "$OUTPUT_PATH" || exit $?
pbcopy < "$OUTPUT_PATH"
cat "$OUTPUT_PATH"

echo
echo "SQP WBR summary copied to clipboard and saved to $OUTPUT_PATH"
