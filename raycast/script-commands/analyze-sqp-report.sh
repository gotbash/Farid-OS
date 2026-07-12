#!/bin/bash
# Required parameters: 1
# @raycast.schemaVersion 1
# @raycast.title Analyze SQP Report
# @raycast.mode fullOutput
# @raycast.packageName Farid OS
# @raycast.argument1 { "type": "text", "placeholder": "Absolute path to SQP CSV" }

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ROOT_DIR=$(cd "$SCRIPT_DIR/../.." && pwd)

python3 "$ROOT_DIR/tools/sqp_analyzer.py" "$1" --output /tmp/farid-os-sqp-analysis.md || exit $?
pbcopy < /tmp/farid-os-sqp-analysis.md
cat /tmp/farid-os-sqp-analysis.md

echo
echo "Report copied to clipboard and saved to /tmp/farid-os-sqp-analysis.md"
