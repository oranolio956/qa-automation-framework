#!/usr/bin/env bash
set -euo pipefail

# Fail CI if fixed sleeps are present in automation flows or blocking sleeps in async code

echo "Scanning for forbidden sleep patterns..."

FORBIDDEN_DIRS=(automation/snapchat automation/android)
FAILED=0

for dir in "${FORBIDDEN_DIRS[@]}"; do
  if git ls-files "$dir" | grep -E '\.py$' >/dev/null 2>&1; then
    if rg -n "\btime\.sleep\(\d+(?:\.\d+)?\)" "$dir" -g '!**/tests/**' | cat; then
      echo "ERROR: Fixed numeric time.sleep() calls detected in $dir" >&2
      FAILED=1
    fi
    # Blocking sleep anywhere in async def
    if rg -n "async\s+def[\s\S]*?time\.sleep\(" "$dir" -U -g '!**/tests/**' | cat; then
      echo "ERROR: Blocking time.sleep() used inside async def in $dir" >&2
      FAILED=1
    fi
  fi
done

if [[ "$FAILED" -ne 0 ]]; then
  echo "Forbidden sleep patterns found. See above." >&2
  exit 1
fi

echo "No forbidden sleep patterns found."

