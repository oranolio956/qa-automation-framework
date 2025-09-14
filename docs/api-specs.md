# API Specifications

This document defines the primary REST endpoints, GraphQL schema, WebSocket events, and error conventions.

## REST Endpoints (v1)

- POST /api/v1/contractors/register
  - Body: `{ email, password?, auth0Token?, referralCode? }`
  - Response: `201 { contractorId }`
  - Notes: prefer Auth0 hosted signup; fallback local for dev only

- GET /api/v1/contractors/{id}/status
  - Response: `{ status, currentStep, completedSteps, verification: { insurance, license, bank } }`

- PATCH /api/v1/contractors/{id}/progress
  - Body: `{ currentStep, completedSteps, validationErrors? }`
  - Response: `200`

- POST /api/v1/contractors/{id}/documents/upload-intent
  - Body: `{ type, mimeType, size, checksum }`
  - Response: `{ documentId, uploadUrl, expiresAt }`

- POST /api/v1/verification/insurance
  - Body: `{ contractorId, provider, policyNumber, coverageType[], expirationDate? }`
  - Response: `{ isValid, confidence, errors[], expirationWarning?, renewalReminder? }`

- POST /api/v1/verification/bank
  - Body: `{ contractorId, method }` → returns Plaid Link token or micro-deposit instructions
  - Response: `{ linkToken? , verificationStatus }`

- POST /api/v1/email-lists/import
  - Body: `{ contractorId, listName, csvUrl | csvBase64 }`
  - Response: `{ importId, status }`

### Webhooks

- POST /webhooks/trustlayer
- POST /webhooks/veriforce
- POST /webhooks/plaid
  - Verify signatures, ensure idempotency via `Idempotency-Key` and provider event ids

## GraphQL Schema (Gateway)

Schema excerpt for onboarding flows.

```graphql
type Contractor {
  id: ID!
  status: ContractorStatus!
  profile: BusinessProfile
  verification: VerificationSnapshot!
  achievements: [Achievement!]!
}

type BusinessProfile {
  legalName: String!
  dbaName: String
  phone: String
  email: String
  website: String
  address: Address
}

type Address { line1: String, line2: String, city: String, state: String, postalCode: String, country: String }

enum ContractorStatus { PENDING IN_REVIEW VERIFIED REJECTED }

type VerificationSnapshot {
  insurance: VerificationResult
  license: VerificationResult
  bank: BankVerification
}

type VerificationResult { isValid: Boolean!, confidence: Float!, errors: [String!] }

type BankVerification { status: String!, method: String!, verificationDate: String }

type UploadIntent { documentId: ID!, uploadUrl: String!, expiresAt: String! }

type Query {
  contractor(id: ID!): Contractor
  meContractor: Contractor
}

input RegisterContractorInput { email: String!, referralCode: String }
input SaveStepInput { contractorId: ID!, step: Int!, data: JSON }
input UploadIntentInput { contractorId: ID!, type: String!, mimeType: String!, size: Int!, checksum: String! }

type Mutation {
  registerContractor(input: RegisterContractorInput!): Contractor!
  saveStep(input: SaveStepInput!): Boolean!
  createUploadIntent(input: UploadIntentInput!): UploadIntent!
  verifyInsurance(contractorId: ID!, provider: String!, policyNumber: String!): VerificationResult!
  startBankVerification(contractorId: ID!, method: String!): BankVerification!
}
```

## WebSocket Events (Socket.io)

```ts
interface WebSocketEvents {
  'verification:started': { documentId: string; type: string };
  'verification:completed': { documentId: string; result: { isValid: boolean; confidence: number; errors: string[] } };
  'progress:updated': { contractorId: string; progress: number };
  'badge:unlocked': { contractorId: string; badge: { id: string; title: string } };
}
```

## Error Model

- Use RFC 7807 Problem Details
  - `type`, `title`, `status`, `detail`, `instance`, `errors[]`
- Validation failures return `422` with field error map
- Include `requestId`/`traceId` on all responses

## Auth & Rate Limits

- OAuth2/OIDC via Auth0; JWT bearer required for all private endpoints
- Kong rate limits: `60 rpm` per IP unauthenticated, `600 rpm` per user authenticated; bursts allowed

## Idempotency & Concurrency

- Idempotency-Key supported on POST/PUT; server stores recent keys for 24h
- ETags and If-Match for document metadata updates

## Versioning

- SemVer-style API version in URL for REST and in GraphQL schema via deprecations

