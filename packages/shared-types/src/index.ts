export interface VerificationResult {
  isValid: boolean;
  confidence: number;
  errors: string[];
  expirationWarning?: string;
  renewalReminder?: string;
}

export interface UploadIntentResponse {
  documentId: string;
  uploadUrl: string;
  expiresAt: string;
}

export type ContractorStatus = 'PENDING' | 'IN_REVIEW' | 'VERIFIED' | 'REJECTED';

