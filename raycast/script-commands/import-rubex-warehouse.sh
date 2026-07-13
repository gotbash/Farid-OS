#!/bin/bash
# @raycast.schemaVersion 1
# @raycast.title Import Rubex Warehouse
# @raycast.mode fullOutput
# @raycast.packageName Farid OS

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ROOT_DIR=$(cd "$SCRIPT_DIR/../.." && pwd)
OUTPUT_PATH=/tmp/farid-os-warehouse-import.md

cd "$ROOT_DIR" || exit 1
PYTHONDONTWRITEBYTECODE=1 python3 tools/warehouse_importer.py --output "$OUTPUT_PATH" || exit $?
pbcopy < "$OUTPUT_PATH"
cat "$OUTPUT_PATH"

echo
echo "Warehouse import summary copied to clipboard and saved to $OUTPUT_PATH"
