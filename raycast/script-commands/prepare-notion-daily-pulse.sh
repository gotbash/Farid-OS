#!/bin/bash
# Required parameters: 1
# @raycast.schemaVersion 1
# @raycast.title Prepare Notion Daily Pulse
# @raycast.mode compact
# @raycast.packageName Farid OS
# @raycast.argument1 { "type": "text", "placeholder": "Daily headline" }
today=$(date +%Y-%m-%d)
cat <<EOF | pbcopy
## Daily Pulse - ${today}

**Executive summary:** $1

**KPI movement vs yesterday / target:** [MISSING]

**What changed:** [MISSING]

**Top risks:** [MISSING]

**Top 3 priorities today:** [MISSING]

**Escalations / decisions needed:** [MISSING]

**Missing inputs:** [MISSING]

**Sources:** [VERIFY]
EOF
echo "Daily Pulse template copied - paste into Decision & Report Log"
