#!/bin/bash
# Required parameters: 1
# @raycast.schemaVersion 1
# @raycast.title Prepare Notion RCA
# @raycast.mode compact
# @raycast.packageName Farid OS
# @raycast.argument1 { "type": "text", "placeholder": "Problem statement" }
today=$(date +%Y-%m-%d)
cat <<EOF | pbcopy
## RCA - ${today}

**Problem statement:** $1

**Observed symptoms:** [MISSING]

**5 Whys chain:** [MISSING]

**Confirmed root cause:** [MISSING]

**Immediate mitigation:** [MISSING]

**Long-term prevention:** [MISSING]

**Validation step:** [MISSING]

**Open questions / missing inputs:** [MISSING]

**Sources:** [VERIFY]
EOF
echo "RCA template copied - paste into Decision & Report Log"
