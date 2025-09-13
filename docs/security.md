# Security & Compliance

This document defines authentication, authorization, encryption, auditing, compliance controls (GDPR/CCPA/PCI), and a high-level threat model.

## Authentication & MFA

- Auth0 OIDC for user auth (contractors and staff)
- MFA: SMS, TOTP, email magic link allowed; enforce MFA at first sensitive action
- Session: short-lived access tokens; refresh via rotating refresh tokens; device binding

## Authorization

- RBAC: roles `contractor`, `reviewer`, `admin`
- ABAC for resource scoping: contractorId must match token subject claims
- Kong enforces scopes; services re-check claims for defense in depth

## Encryption

- In transit: TLS 1.3 for external; mTLS for service-to-service
- At rest: AES-256-GCM for S3 objects, EBS volumes encrypted; Postgres TDE or tablespace encryption
- Field-level encryption for sensitive fields (tax_id) using application-layer envelope (KMS)
- Key rotation every 180 days; audit rotations

## Secrets Management

- Store secrets in cloud Secrets Manager; never in env files committed to VCS
- Access via IAM roles; least privilege; short-lived credentials

## Audit & Logging

- Log all sensitive actions (verification decisions, data exports, role changes)
- Retention: 24 months; immutable storage (WORM) for tamper resistance
- Correlate with traceId; send to SIEM; alert on anomalous patterns

## Data Retention & Privacy

- GDPR/CCPA consent tracking; purpose-limited processing for documents and emails
- Data minimization: store only necessary provider payload fields
- Right to erasure: cascading delete across Postgres, MongoDB, S3, Redis; tombstones for audit
- Retention policies per data class; automatic lifecycle rules in S3

## PCI DSS Touchpoints

- No card data stored in platform; use Stripe/Square hosted fields for any payments
- Bank verification through Plaid; do not store routing/account numbers

## Vulnerability Management

- SAST/DAST in CI (ESLint, npm audit, Trivy, OWASP ZAP)
- Dependency pinning and weekly updates; renovate bot
- Security headers: CSP (nonce-based), HSTS, XFO deny, Referrer-Policy, COOP/COEP where applicable

## Threat Model (STRIDE)

- Spoofing: OIDC tokens, MFA, device checks; mTLS internally
- Tampering: signatures on webhooks; idempotency keys; request body hashing
- Repudiation: non-repudiation via audit logs and webhook receipts
- Information disclosure: field-level encryption; least-privilege IAM; token scoping
- Denial of service: Kong rate limits, WAF, autoscaling, backpressure
- Elevation of privilege: strict RBAC/ABAC, code reviews, secret scanning

## Webhooks Security

- Verify provider signatures; replay protection via nonce + timestamp; 5-minute window
- Store raw payloads for audit; compute HMAC and store alongside

## Compliance Reporting

- Automated reports for access logs, data deletions, verification outcomes
- Evidence collection for auditors: CI logs, IaC change history, key rotation logs

