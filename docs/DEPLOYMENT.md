# Deployment Guide (Fly.io and Others)

## Prerequisites

- Install flyctl: `curl -L https://fly.io/install.sh | sh`
- Create Fly account and org; login: `flyctl auth login`
- Set `FLY_API_TOKEN` GitHub secret for CI

## Apps and Services

- apps/web (Next.js) → `apps/web/fly.toml`
- services/contractor-service → `services/contractor-service/fly.toml`
- services/document-service → `services/document-service/fly.toml`
- services/realtime-service → `services/realtime-service/fly.toml`
- services/verification-service → `services/verification-service/fly.toml`
- services/gamification-service → `services/gamification-service/fly.toml`

## Environment Variables & Secrets

- Set per app via `flyctl secrets set KEY=VALUE` (examples in `.env.example`)
- Realtime internal:
  - `INTERNAL_EMIT_TOKEN`
  - `REALTIME_EMIT_URL`
- Verification webhooks:
  - `WEBHOOK_SECRET`
  - `CONTRACTOR_BASE`

## Deploy Locally (Manual)

- Per directory: `flyctl launch` (skip creation if toml present) then `flyctl deploy --remote-only`

## GitHub Actions CI/CD

- Workflow: `.github/workflows/fly-deploy.yml` runs a matrix deploy on main
- Requires `FLY_API_TOKEN` secret

## Other Platforms

- Docker images build using provided Dockerfiles; deploy to AWS ECS, GCP Cloud Run, or Kubernetes
- For K8s: use Dockerfiles and create Deployments/Services; optional Kong Ingress with `kong/kong.yml` as reference