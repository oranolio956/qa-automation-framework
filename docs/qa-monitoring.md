# QA, Testing, Monitoring

This document specifies testing strategies across levels, CI quality gates, and monitoring/alerting practices.

## Testing Strategy

- Unit Tests: Jest + React Testing Library for UI; Jest for services
- Integration/E2E: Cypress for PWA flows; supertest for service APIs
- Contract Tests: Pact between BFF and services
- Performance: Lighthouse CI for PWA; k6 or Artillery for API load
- Security: OWASP ZAP baseline scans; dependency scanning; secret scanning

## CI Quality Gates

- Lint and typecheck must pass
- Unit tests coverage ≥ 80% statements/branches for changed files
- E2E smoke suite on PR; full regression nightly
- No critical/high vulnerabilities allowed
- Block deploy if error rate or latency regression detected in canary

## Test Data & Environments

- Seed scripts for contractors, documents, and verification mocks
- Isolated databases per test run where possible; use Testcontainers
- Feature flags to simulate provider failures and edge cases

## Monitoring & Observability

- Tracing: OpenTelemetry SDKs → collector → vendor backend (Datadog/New Relic) or Tempo/Jaeger
- Metrics: RED/USE dashboards per service; SLOs with alerting (error rate, p95 latency, saturation)
- Logging: structured JSON; correlation ids; log sampling for noisy paths

### Example SLOs

- BFF GraphQL p95 < 300ms (99.9% availability monthly)
- Document upload success rate ≥ 99.5%
- Verification webhook processing success ≥ 99.9% with ≤ 2 min p95 latency

## Alerting

- Multi-channel (PagerDuty/Slack/Email)
- Alert policies: error rate spikes, latency breaches, queue backlogs, disk pressure, TLS expiry, webhook failures

## Release Management

- Canary with 5% traffic for 15 minutes; auto-promote on green
- Feature flags for risky features; kill switches
- Post-incident reviews; action items tracked

