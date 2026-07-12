#!/bin/bash
# Required parameters: 1
# @raycast.schemaVersion 1
# @raycast.title Amazon Search
# @raycast.mode silent
# @raycast.packageName Farid OS
# @raycast.argument1 { "type": "text", "placeholder": "ASIN, keyword, or product" }
query=$(python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1]))' "$1")
open "https://www.amazon.com/s?k=${query}"

