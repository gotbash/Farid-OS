#!/bin/bash
# @raycast.schemaVersion 1
# @raycast.title Import Product Profiles
# @raycast.mode fullOutput
# @raycast.packageName Farid OS

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ROOT_DIR=$(cd "$SCRIPT_DIR/../.." && pwd)

cd "$ROOT_DIR" || exit 1
PYTHONDONTWRITEBYTECODE=1 python3 tools/warehouse_importer.py >/dev/null || exit $?
PYTHONDONTWRITEBYTECODE=1 python3 tools/product_profile.py import || exit $?
echo
PYTHONDONTWRITEBYTECODE=1 python3 tools/product_profile.py report
