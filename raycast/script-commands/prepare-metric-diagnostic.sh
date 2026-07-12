#!/bin/bash
# Required parameters: 1
# @raycast.schemaVersion 1
# @raycast.title Prepare Metric Diagnostic
# @raycast.mode compact
# @raycast.packageName Farid OS
# @raycast.argument1 { "type": "text", "placeholder": "Observed metric change" }
today=$(date +%Y-%m-%d)
cat <<EOF | pbcopy
## Amazon Metric Diagnostic — ${today}

**Observed facts:** $1

**Ranked cause tree:** [MISSING]

**Checks required:** [MISSING]

**Prioritized actions:** [MISSING]

**Expected impact / risk / reversibility:** [MISSING]

**Owner / measurement window:** [MISSING]

**Sources:** [VERIFY]
EOF
echo "Diagnostic template copied — use with the Decision Engine"

