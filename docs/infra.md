# Infrastructure & DevOps

This document outlines Terraform structure, environments, CI/CD, Kubernetes, scaling, gateway, and multi-region design.

## Terraform Layout

- `infra/` root with environment workspaces: `dev/`, `staging/`, `prod/`
- Reusable modules:
  - `modules/network` (VPC, subnets, NAT, gateways)
  - `modules/eks` or `modules/gke` (Kubernetes cluster, node groups)
  - `modules/datastores` (Postgres managed DB, MongoDB Atlas, Redis, S3)
  - `modules/kong` (Ingress GW, rate limits, plugins)
  - `modules/observability` (Prometheus/Grafana/Tempo or vendor agents)
  - `modules/cdn` (Cloudflare zones, caching)

State stored in remote backend (Terraform Cloud or S3 + DynamoDB lock). Use versioned modules and tagged releases.

## Environments

- Separate accounts/projects per env; isolated VPCs
- Secrets per env; CI injects only required scopes

## CI/CD

- GitHub Actions (or GitLab CI):
  - Build, lint, test → docker build → push to registry
  - Trivy image scan; Snyk dependency scan
  - Deploy via ArgoCD/Flux (GitOps) or direct kubectl with canary
  - Migrations: run `prisma migrate deploy` or `knex` job as pre-deploy hook

## Kubernetes

- Namespaces per service: `bff`, `contractor`, `document`, `verification`, `realtime`, `gamification`, `notification`
- HPA based on CPU and custom metrics (RPS, queue depth)
- PodDisruptionBudgets, readiness/liveness probes, resource requests/limits
- Service mesh optional for mTLS and retries (Istio/Linkerd)

## Gateway: Kong

- Plugins: JWT/OIDC auth, rate limiting, ip-restriction for admin routes, request/response transformer
- Observability: log to ELK/Datadog; status endpoints

## Data Stores

- PostgreSQL managed service with HA (multi-AZ), PITR enabled
- MongoDB Atlas with M10+ cluster, backup and TLS
- Redis managed (ElastiCache/MemoryStore) with TLS and auth
- S3 buckets with versioning, lifecycle rules, access logs

## Scaling & Multi-Region

- Active-active for CDN, read-heavy services with global load balancing
- Active-passive for verification providers; failover runbooks
- Data residency: pin PII to regions as needed; cross-region read replicas for Postgres

## Secrets & Config

- 12-factor envs; sealed-secrets or external-secrets for K8s
- KMS for envelope encryption; automatic rotation

## Disaster Recovery

- RPO: ≤ 15 minutes; RTO: ≤ 60 minutes
- Regular restore drills; document playbooks

