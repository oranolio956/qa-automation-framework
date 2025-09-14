#!/usr/bin/env bash
set -euo pipefail

export PATH="$HOME/.fly/bin:$PATH"

apps=(
  "apps/web"
  "services/contractor-service"
  "services/document-service"
  "services/realtime-service"
  "services/verification-service"
  "services/gamification-service"
)

for dir in "${apps[@]}"; do
  echo "Deploying $dir"
  (cd "$dir" && flyctl deploy --remote-only)
done

