#!/bin/bash
# Required parameters: 1
# @raycast.schemaVersion 1
# @raycast.title Analyze Search Term Report
# @raycast.mode fullOutput
# @raycast.packageName Farid OS
# @raycast.argument1 { "type": "text", "placeholder": "Absolute path to CSV" }

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ROOT_DIR=$(cd "$SCRIPT_DIR/../.." && pwd)

python3 "$ROOT_DIR/tools/search_term_analyzer.py" "$1" --output /tmp/farid-os-search-term-analysis.md || exit $?
pbcopy < /tmp/farid-os-search-term-analysis.md
cat /tmp/farid-os-search-term-analysis.md

echo
echo "Report copied to clipboard and saved to /tmp/farid-os-search-term-analysis.md"
