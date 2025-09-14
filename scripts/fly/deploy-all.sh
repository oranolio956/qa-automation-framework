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
  (
    cd "$dir" || exit 1
    appName=$(awk -F '"' '/^app\s*=\s*"/{print $2}' fly.toml)
    if [ -n "$appName" ]; then
      if ! flyctl apps show "$appName" >/dev/null 2>&1; then
        echo "Creating app $appName"
        flyctl apps create "$appName"
      fi
    fi
    flyctl deploy --remote-only 2>&1 | tee -a /workspace/fly_deploy.log
  )
done

