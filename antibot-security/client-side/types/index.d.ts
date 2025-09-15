/**
 * TypeScript Declaration Files for Behavioral Analytics Components
 * Provides comprehensive type safety for all client-side modules
 */

// =============================================================================
// Browser Agent Types
// =============================================================================

export interface TouchEventData {
  identifier: number;
  clientX: number;
  clientY: number;
  force?: number;
  radiusX?: number;
  radiusY?: number;
  rotationAngle?: number;
}

export interface BehavioralEventData {
  type: 'mouse' | 'keyboard' | 'touch' | 'scroll' | 'focus' | 'visibility' | 'performance';
  subtype?: string;
  timestamp: number;
  sessionId: string;
  pageUrl: string;
  referrer?: string;
  x?: number;
  y?: number;
  velocity?: number;
  acceleration?: number;
  dwellTime?: number;
  scrollSpeed?: number;
  direction?: string;
  touches?: TouchEventData[];
  key?: string;
  code?: string;
  button?: number;
  buttons?: number;
  altKey?: boolean;
  ctrlKey?: boolean;
  shiftKey?: boolean;
  metaKey?: boolean;
  repeat?: boolean;
  deltaX?: number;
  deltaY?: number;
  deltaZ?: number;
  deltaMode?: number;
  scrollX?: number;
  scrollY?: number;
  hidden?: boolean;
  visibilityState?: string;
  focused?: boolean;
  name?: string;
  duration?: number;
  startTime?: number;
  touchCount?: number;
}

export interface DeviceFingerprintData {
  timestamp: number;
  hash: string;
  userAgent: string;
  language: string;
  languages: string[];
  platform: string;
  cookieEnabled: boolean;
  doNotTrack: string | null;
  hardwareConcurrency: number;
  maxTouchPoints: number;
  memory?: number;
  screen: {
    width: number;
    height: number;
    availWidth: number;
    availHeight: number;
    colorDepth: number;
    pixelDepth: number;
    orientation?: string;
  };
  timezone: {
    offset: number;
    timezone: string;
    locale: string;
  };
  webgl?: any;
  canvas?: {
    dataURL: string;
    hash: string;
  };
  audio?: {
    fingerprint: string;
    sampleRate: number;
    maxChannelCount: number;
  };
  mediaDevices?: any[];
  connection?: {
    effectiveType?: string;
    type?: string;
    downlink?: number;
    rtt?: number;
    saveData?: boolean;
  };
}

export interface TLSFingerprintData {
  timestamp: number;
  supportedProtocols: string[];
  cipherSuites: string[];
  compression: any;
  extensions: string[];
}

export interface PerformanceMetrics {
  eventCollectionTime: number;
  dataTransmissionTime: number;
  totalEvents: number;
  avgEventCollectionTime?: number;
  bufferSize?: number;
  sessionDuration?: number;
}

export interface BehavioralDataPayload {
  sessionId: string;
  deviceFingerprint: DeviceFingerprintData | null;
  tlsFingerprint: TLSFingerprintData | null;
  events: BehavioralEventData[];
  metadata: {
    userAgent: string;
    timestamp: number;
    sessionDuration: number;
    timeSinceLastActivity: number;
    performanceMetrics: PerformanceMetrics;
    consentGiven: boolean;
    collectionMode: 'minimal' | 'standard' | 'comprehensive';
    privacyMode: boolean;
  };
}

export interface RiskAction {
  type: 'challenge' | 'block' | 'monitor' | 'allow';
  challengeType?: string;
  reason?: string;
  level?: string;
  confidence: number;
}

export interface RiskAssessmentResponse {
  sessionId: string;
  riskScore: number;
  confidence: number;
  actions: RiskAction[];
  reasons: string[];
  modelVersion: string;
  processingTimeMs: number;
  timestamp: string;
}

export interface BehavioralAnalyticsConfig {
  apiEndpoint?: string;
  batchSize?: number;
  flushInterval?: number;
  enableMouseTracking?: boolean;
  enableKeyboardTracking?: boolean;
  enableScrollTracking?: boolean;
  enableTouchTracking?: boolean;
  enableDeviceFingerprinting?: boolean;
  privacyMode?: boolean;
  collectionMode?: 'minimal' | 'standard' | 'comprehensive';
  consentRequired?: boolean;
  retryAttempts?: number;
  retryDelay?: number;
  compressionEnabled?: boolean;
  encryptionEnabled?: boolean;
  rateLimitPerSecond?: number;
  maxEventBufferSize?: number;
  offlineStorageEnabled?: boolean;
  performanceThreshold?: number;
}

// =============================================================================
// Mobile SDK Types
// =============================================================================

export interface TouchGestureMobileData {
  identifier: number;
  locationX: number;
  locationY: number;
  pageX: number;
  pageY: number;
  timestamp: number;
  pressure?: number;
  size?: number;
  velocity?: number;
  acceleration?: number;
}

export interface BehavioralEventMobile {
  type: 'touch' | 'gesture' | 'device' | 'sensor' | 'app_state' | 'network';
  subtype?: string;
  timestamp: number;
  sessionId: string;
  data: any;
  deviceFingerprint?: string;
}

export interface DeviceFingerprintMobile {
  deviceId: string;
  platform: string;
  version: string;
  model: string;
  brand: string;
  buildNumber: string;
  bundleId: string;
  deviceName: string;
  systemName: string;
  systemVersion: string;
  timezone: string;
  locale: string;
  screenDimensions: {
    width: number;
    height: number;
    scale: number;
    fontScale: number;
  };
  networkInfo: {
    type: string;
    isConnected: boolean;
    isInternetReachable: boolean;
  };
  sensors: {
    hasAccelerometer: boolean;
    hasGyroscope: boolean;
    hasMagnetometer: boolean;
    hasBarometer: boolean;
  };
  security: {
    isEmulator: boolean;
    isRooted: boolean;
    isDebuggingEnabled: boolean;
    hasMockLocation: boolean;
  };
  hash: string;
}

export interface EmulatorDetectionResult {
  isEmulator: boolean;
  confidence: number;
  indicators: string[];
  riskLevel: 'low' | 'medium' | 'high';
}

export interface BehavioralAnalyticsMobileConfig {
  apiEndpoint?: string;
  sessionTimeout?: number;
  batchSize?: number;
  flushInterval?: number;
  enableTouchTracking?: boolean;
  enableGestureAnalysis?: boolean;
  enableEmulatorDetection?: boolean;
  enableSensorData?: boolean;
  privacyMode?: boolean;
  consentRequired?: boolean;
  performanceThreshold?: number;
  offlineStorageEnabled?: boolean;
}

// =============================================================================
// Data Transmission Types
// =============================================================================

export interface TransmissionConfig {
  apiEndpoint: string;
  maxRetries: number;
  retryDelay: number;
  batchSize: number;
  compressionEnabled: boolean;
  encryptionEnabled: boolean;
  rateLimitPerSecond: number;
  timeoutMs: number;
  offlineStorageKey: string;
  maxOfflineStorage: number;
  enablePersistence: boolean;
  compressionThreshold: number;
  encryptionKey?: string;
  authToken?: string;
}

export interface TransmissionPayload {
  sessionId: string;
  timestamp: number;
  data: any;
  metadata: {
    platform: string;
    version: string;
    compressionUsed?: string;
    encryptionUsed?: string;
    batchSize: number;
    retryAttempt?: number;
  };
}

export interface TransmissionResult {
  success: boolean;
  statusCode?: number;
  response?: any;
  error?: string;
  transmissionTime: number;
  retryAttempts: number;
}

export interface QueuedTransmission {
  id: string;
  payload: TransmissionPayload;
  timestamp: number;
  retries: number;
  priority: 'low' | 'medium' | 'high' | 'critical';
}

export interface TransmissionMetrics {
  totalTransmissions: number;
  successfulTransmissions: number;
  failedTransmissions: number;
  avgTransmissionTime: number;
  totalDataTransmitted: number;
  compressionRatio: number;
  retryRate: number;
  offlineQueueSize: number;
}

// =============================================================================
// Event Types for DOM
// =============================================================================

declare global {
  interface DocumentEventMap {
    'antibot:riskScore': CustomEvent<{
      riskScore: number;
      actions: RiskAction[];
      sessionId: string;
    }>;
    'antibot:challenge': CustomEvent<{
      type: string;
      sessionId: string;
    }>;
    'antibot:blocked': CustomEvent<{
      reason: string;
      sessionId: string;
    }>;
    'antibot:consent': CustomEvent<{
      granted: boolean;
      sessionId: string;
    }>;
    'antibot:consentRequired': CustomEvent<{
      sessionId: string;
      privacyPolicy: string;
    }>;
  }

  interface Window {
    BehavioralAnalytics: typeof BehavioralAnalytics;
    DataTransmissionModule: typeof DataTransmissionModule;
  }
}

// =============================================================================
// Main Class Declarations
// =============================================================================

export declare class BehavioralAnalytics {
  constructor(config?: BehavioralAnalyticsConfig);
  
  public grantConsent(): void;
  public revokeConsent(): void;
  public flush(): void;
  public getSessionInfo(): { 
    sessionId: string; 
    consentGiven: boolean; 
    metrics: PerformanceMetrics 
  };
  public destroy(): void;
  
  private config: Required<BehavioralAnalyticsConfig>;
  private sessionId: string;
  private events: BehavioralEventData[];
  private deviceFingerprint: DeviceFingerprintData | null;
  private tlsFingerprint: TLSFingerprintData | null;
  private startTime: number;
  private lastActivity: number;
  private performanceMetrics: PerformanceMetrics;
  private consentGiven: boolean;
  private initialized: boolean;
}

export declare class DataTransmissionModule {
  constructor(config: Partial<TransmissionConfig>);
  
  public transmit(
    sessionId: string, 
    data: any, 
    priority?: 'low' | 'medium' | 'high' | 'critical'
  ): Promise<string>;
  
  public transmitBatch(
    sessionId: string,
    dataItems: any[],
    priority?: 'low' | 'medium' | 'high' | 'critical'
  ): Promise<string[]>;
  
  public flush(): Promise<void>;
  public getMetrics(): TransmissionMetrics;
  public getQueueStatus(): {
    totalItems: number;
    itemsByPriority: Record<string, number>;
    oldestItem?: number;
    newestItem?: number;
  };
  public clearQueue(): void;
  public updateConfig(newConfig: Partial<TransmissionConfig>): void;
  public destroy(): void;
  
  private config: TransmissionConfig;
  private transmissionQueue: QueuedTransmission[];
  private rateLimiter: number;
  private isOnline: boolean;
  private metrics: TransmissionMetrics;
}

// =============================================================================
// React Native Hook Types
// =============================================================================

export interface UseBehavioralAnalyticsReturn {
  sessionInfo: any;
  grantConsent: () => Promise<void>;
  revokeConsent: () => Promise<void>;
  flush: () => void;
  analytics: any;
}

export declare function useBehavioralAnalytics(
  config?: Partial<BehavioralAnalyticsMobileConfig>
): UseBehavioralAnalyticsReturn;

// =============================================================================
// React Component Types
// =============================================================================

export interface ConsentModalProps {
  visible: boolean;
  onConsent: (granted: boolean) => void;
}

export declare const ConsentModal: React.FC<ConsentModalProps>;

// =============================================================================
// Utility Types
// =============================================================================

export type CollectionMode = 'minimal' | 'standard' | 'comprehensive';
export type Priority = 'low' | 'medium' | 'high' | 'critical';
export type RiskLevel = 'low' | 'medium' | 'high';
export type Platform = 'web' | 'android' | 'ios' | 'node';

// =============================================================================
// Error Types
// =============================================================================

export class BehavioralAnalyticsError extends Error {
  constructor(message: string, public code: string, public context?: any) {
    super(message);
    this.name = 'BehavioralAnalyticsError';
  }
}

export class TransmissionError extends Error {
  constructor(
    message: string, 
    public statusCode?: number, 
    public retryAttempts?: number
  ) {
    super(message);
    this.name = 'TransmissionError';
  }
}

export class ConsentError extends Error {
  constructor(message: string, public required: boolean) {
    super(message);
    this.name = 'ConsentError';
  }
}

// =============================================================================
// Configuration Presets
// =============================================================================

export const ConfigPresets: {
  minimal: BehavioralAnalyticsConfig;
  standard: BehavioralAnalyticsConfig;
  comprehensive: BehavioralAnalyticsConfig;
  highPrivacy: BehavioralAnalyticsConfig;
  lowLatency: BehavioralAnalyticsConfig;
  mobileOptimized: BehavioralAnalyticsMobileConfig;
} = {
  minimal: {
    collectionMode: 'minimal',
    privacyMode: true,
    enableMouseTracking: false,
    enableKeyboardTracking: false,
    enableScrollTracking: false,
    enableTouchTracking: true,
    enableDeviceFingerprinting: false,
    consentRequired: true,
    batchSize: 10,
    flushInterval: 10000,
    rateLimitPerSecond: 20,
  },
  
  standard: {
    collectionMode: 'standard',
    privacyMode: false,
    enableMouseTracking: true,
    enableKeyboardTracking: true,
    enableScrollTracking: true,
    enableTouchTracking: true,
    enableDeviceFingerprinting: true,
    consentRequired: true,
    batchSize: 50,
    flushInterval: 5000,
    rateLimitPerSecond: 100,
  },
  
  comprehensive: {
    collectionMode: 'comprehensive',
    privacyMode: false,
    enableMouseTracking: true,
    enableKeyboardTracking: true,
    enableScrollTracking: true,
    enableTouchTracking: true,
    enableDeviceFingerprinting: true,
    consentRequired: false,
    batchSize: 100,
    flushInterval: 2000,
    rateLimitPerSecond: 200,
    compressionEnabled: true,
    encryptionEnabled: true,
  },
  
  highPrivacy: {
    collectionMode: 'minimal',
    privacyMode: true,
    enableMouseTracking: false,
    enableKeyboardTracking: false,
    enableScrollTracking: false,
    enableTouchTracking: false,
    enableDeviceFingerprinting: false,
    consentRequired: true,
    batchSize: 5,
    flushInterval: 30000,
    rateLimitPerSecond: 10,
  },
  
  lowLatency: {
    collectionMode: 'standard',
    batchSize: 20,
    flushInterval: 1000,
    rateLimitPerSecond: 200,
    performanceThreshold: 5,
    compressionEnabled: false,
    retryAttempts: 1,
    retryDelay: 500,
  },
  
  mobileOptimized: {
    batchSize: 20,
    flushInterval: 15000,
    enableSensorData: false,
    enableGestureAnalysis: true,
    enableEmulatorDetection: true,
    performanceThreshold: 100,
    offlineStorageEnabled: true,
  }
};

// =============================================================================
// Validation Schemas (for runtime type checking)
// =============================================================================

export interface ValidationSchema {
  validateConfig(config: any): boolean;
  validateEvent(event: any): boolean;
  validateFingerprint(fingerprint: any): boolean;
  validateTransmissionPayload(payload: any): boolean;
}

export declare const Validator: ValidationSchema;

// =============================================================================
// Constants
// =============================================================================

export const CONSTANTS = {
  MAX_EVENT_BUFFER_SIZE: 10000,
  MAX_RETRY_ATTEMPTS: 5,
  MIN_FLUSH_INTERVAL: 1000,
  MAX_FLUSH_INTERVAL: 300000,
  DEFAULT_BATCH_SIZE: 50,
  DEFAULT_RATE_LIMIT: 100,
  PERFORMANCE_THRESHOLD: 10,
  SESSION_TIMEOUT: 1800000, // 30 minutes
  OFFLINE_STORAGE_LIMIT: 1000,
  COMPRESSION_THRESHOLD: 1024,
  ENCRYPTION_KEY_LENGTH: 32,
} as const;

// =============================================================================
// Feature Detection
// =============================================================================

export interface FeatureSupport {
  webGL: boolean;
  webWorkers: boolean;
  webCrypto: boolean;
  compressionStreams: boolean;
  performanceObserver: boolean;
  deviceMotion: boolean;
  touchEvents: boolean;
  pointerEvents: boolean;
  serviceWorkers: boolean;
  webRTC: boolean;
  localStorage: boolean;
  indexedDB: boolean;
}

export declare function detectFeatures(): FeatureSupport;

// =============================================================================
// Debugging and Development
// =============================================================================

export interface DebugOptions {
  enableLogging: boolean;
  logLevel: 'error' | 'warn' | 'info' | 'debug' | 'verbose';
  logToConsole: boolean;
  logToStorage: boolean;
  enableMetrics: boolean;
  enablePerformanceMonitoring: boolean;
}

export declare class DebugLogger {
  constructor(options: DebugOptions);
  
  error(message: string, data?: any): void;
  warn(message: string, data?: any): void;
  info(message: string, data?: any): void;
  debug(message: string, data?: any): void;
  verbose(message: string, data?: any): void;
  
  getLogHistory(): any[];
  exportLogs(): string;
  clearLogs(): void;
}

// =============================================================================
// Export All Types
// =============================================================================

export default BehavioralAnalytics;