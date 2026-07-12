#!/bin/bash
# Required parameters: none
# @raycast.schemaVersion 1
# @raycast.title Validate Notion Record
# @raycast.mode fullOutput
# @raycast.packageName Farid OS

record=$(pbpaste)

if [ -z "$record" ]; then
  echo "BLOCKED: clipboard is empty. Prepare or copy a record first."
  exit 1
fi

missing=""
for field in "Headline:" "Sources:"; do
  if ! printf '%s' "$record" | grep -Fq "$field"; then
    missing="${missing}\n- ${field}"
  fi
done

if printf '%s' "$record" | grep -Eq '\[(MISSING|VERIFY)\]'; then
  echo "BLOCKED: resolve every [MISSING] and [VERIFY] marker before saving to Notion."
  echo
  printf '%s\n' "$record" | grep -E '\[(MISSING|VERIFY)\]' || true
  exit 1
fi

if [ -n "$missing" ]; then
  echo "BLOCKED: required sections are absent:"
  printf '%b\n' "$missing"
  exit 1
fi

echo "READY FOR NOTION"
echo "No unresolved markers found; required WBR sections are present."
echo
echo "Next: create the reviewed record in Decision & Report Log."

