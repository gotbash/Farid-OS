#!/bin/bash
# Required parameters: 1
# @raycast.schemaVersion 1
# @raycast.title Company Research
# @raycast.mode silent
# @raycast.packageName Farid OS
# @raycast.argument1 { "type": "text", "placeholder": "Company name" }
query=$(python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1]))' "$1")
open "https://www.google.com/search?q=${query}+Amazon+brand+company"

