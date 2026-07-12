#!/bin/bash
# Required parameters: 1
# @raycast.schemaVersion 1
# @raycast.title Prepare Notion Decision
# @raycast.mode compact
# @raycast.packageName Farid OS
# @raycast.argument1 { "type": "text", "placeholder": "Decision title" }
today=$(date +%Y-%m-%d)
cat <<EOF | pbcopy
## Decision — ${today}

**Decision:** $1

**Context:** [MISSING]

**Evidence:** [VERIFY]

**Options considered:** [MISSING]

**Chosen action and rationale:** [MISSING]

**Owner / review date:** [MISSING]

**Expected outcome:** [MISSING]

**Risks:** [MISSING]
EOF
echo "Decision template copied — paste into Decision & Report Log"

