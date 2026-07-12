#!/bin/bash
# Required parameters: 1
# @raycast.schemaVersion 1
# @raycast.title Prepare Notion WBR
# @raycast.mode compact
# @raycast.packageName Farid OS
# @raycast.argument1 { "type": "text", "placeholder": "WBR headline" }
today=$(date +%Y-%m-%d)
cat <<EOF | pbcopy
## WBR — ${today}

**Headline:** $1

**KPI vs target / prior period:** [MISSING]

**Validated drivers:** [MISSING]

**Risks:** [MISSING]

**Actions — owner — due date:** [MISSING]

**Decision needed:** [MISSING]

**Sources:** [VERIFY]
EOF
echo "WBR template copied — paste into Decision & Report Log"

