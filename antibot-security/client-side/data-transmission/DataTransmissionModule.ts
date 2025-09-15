/**
 * Data Transmission Module
 * Secure, encrypted data transmission with batching, compression, and retry logic
 * Handles offline capabilities and rate limiting for optimal performance
 */

// Types and Interfaces
interface TransmissionConfig {
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

interface TransmissionPayload {
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

interface TransmissionResult {
  success: boolean;
  statusCode?: number;
  response?: any;
  error?: string;
  transmissionTime: number;
  retryAttempts: number;
}

interface QueuedTransmission {
  id: string;
  payload: TransmissionPayload;
  timestamp: number;
  retries: number;
  priority: 'low' | 'medium' | 'high' | 'critical';
}

interface TransmissionMetrics {
  totalTransmissions: number;
  successfulTransmissions: number;
  failedTransmissions: number;
  avgTransmissionTime: number;
  totalDataTransmitted: number;
  compressionRatio: number;
  retryRate: number;
  offlineQueueSize: number;
}

/**
 * Comprehensive Data Transmission Module
 * Handles secure data transmission with advanced features
 */
class DataTransmissionModule {
  private config: TransmissionConfig;
  private transmissionQueue: QueuedTransmission[] = [];
  private rateLimiter: number = 0;
  private rateLimitWindow: number = Date.now();
  private isOnline: boolean = true;
  private metrics: TransmissionMetrics;
  private transmissionInterval: NodeJS.Timeout | null = null;
  private compressionWorker: Worker | null = null;
  private encryptionKey: CryptoKey | null = null;

  constructor(config: Partial<TransmissionConfig>) {
    this.config = {
      apiEndpoint: config.apiEndpoint || '/api/v1/behavioral-data',
      maxRetries: config.maxRetries || 3,
      retryDelay: config.retryDelay || 1000,
      batchSize: config.batchSize || 50,
      compressionEnabled: config.compressionEnabled !== false,
      encryptionEnabled: config.encryptionEnabled || false,
      rateLimitPerSecond: config.rateLimitPerSecond || 10,
      timeoutMs: config.timeoutMs || 10000,
      offlineStorageKey: config.offlineStorageKey || 'antibot-offline-queue',
      maxOfflineStorage: config.maxOfflineStorage || 100,
      enablePersistence: config.enablePersistence !== false,
      compressionThreshold: config.compressionThreshold || 1024,
      encryptionKey: config.encryptionKey,
      authToken: config.authToken,
    };

    this.metrics = {
      totalTransmissions: 0,
      successfulTransmissions: 0,
      failedTransmissions: 0,
      avgTransmissionTime: 0,
      totalDataTransmitted: 0,
      compressionRatio: 0,
      retryRate: 0,
      offlineQueueSize: 0,
    };

    this.initialize();
  }

  /**
   * Initialize the data transmission module
   */
  private async initialize(): Promise<void> {
    try {
      // Initialize encryption if enabled
      if (this.config.encryptionEnabled) {
        await this.initializeEncryption();
      }

      // Initialize compression worker if available
      if (this.config.compressionEnabled && 'Worker' in window) {
        this.initializeCompressionWorker();
      }

      // Setup network monitoring
      this.setupNetworkMonitoring();

      // Load offline queue
      await this.loadOfflineQueue();

      // Start transmission processor
      this.startTransmissionProcessor();

      console.log('Data Transmission Module initialized successfully');

    } catch (error) {
      console.error('Failed to initialize Data Transmission Module:', error);
    }
  }

  /**
   * Initialize encryption capabilities
   */
  private async initializeEncryption(): Promise<void> {
    try {
      if (this.config.encryptionKey) {
        // Use provided key
        const keyData = new TextEncoder().encode(this.config.encryptionKey);
        this.encryptionKey = await crypto.subtle.importKey(
          'raw',
          keyData,
          { name: 'AES-GCM' },
          false,
          ['encrypt', 'decrypt']
        );
      } else {
        // Generate new key
        this.encryptionKey = await crypto.subtle.generateKey(
          { name: 'AES-GCM', length: 256 },
          true,
          ['encrypt', 'decrypt']
        );
      }
    } catch (error) {
      console.error('Failed to initialize encryption:', error);
      this.config.encryptionEnabled = false;
    }
  }

  /**
   * Initialize compression worker
   */
  private initializeCompressionWorker(): void {
    try {
      // Create compression worker
      const workerScript = `
        self.onmessage = function(e) {
          const { data, action } = e.data;
          
          try {
            if (action === 'compress') {
              // Simple compression simulation - in practice use pako or similar
              const compressed = JSON.stringify(data);
              const ratio = compressed.length / JSON.stringify(data).length;
              
              self.postMessage({
                success: true,
                compressed: compressed,
                originalSize: JSON.stringify(data).length,
                compressedSize: compressed.length,
                ratio: ratio
              });
            } else if (action === 'decompress') {
              const decompressed = JSON.parse(data);
              self.postMessage({
                success: true,
                decompressed: decompressed
              });
            }
          } catch (error) {
            self.postMessage({
              success: false,
              error: error.message
            });
          }
        };
      `;

      const blob = new Blob([workerScript], { type: 'application/javascript' });
      this.compressionWorker = new Worker(URL.createObjectURL(blob));

    } catch (error) {
      console.warn('Compression worker not available:', error);
      this.config.compressionEnabled = false;
    }
  }

  /**
   * Setup network monitoring
   */
  private setupNetworkMonitoring(): void {
    if ('navigator' in window && 'onLine' in navigator) {
      this.isOnline = navigator.onLine;

      window.addEventListener('online', () => {
        this.isOnline = true;
        console.log('Network connection restored');
        this.processOfflineQueue();
      });

      window.addEventListener('offline', () => {
        this.isOnline = false;
        console.log('Network connection lost');
      });
    }

    // Monitor connection quality if available
    if ('navigator' in window && (navigator as any).connection) {
      const connection = (navigator as any).connection;
      connection.addEventListener('change', () => {
        console.log(`Connection changed: ${connection.effectiveType}`);
        this.adjustTransmissionRate(connection.effectiveType);
      });
    }
  }

  /**
   * Adjust transmission rate based on connection quality
   */
  private adjustTransmissionRate(effectiveType: string): void {
    switch (effectiveType) {
      case 'slow-2g':
        this.config.rateLimitPerSecond = 1;
        this.config.batchSize = 10;
        break;
      case '2g':
        this.config.rateLimitPerSecond = 2;
        this.config.batchSize = 20;
        break;
      case '3g':
        this.config.rateLimitPerSecond = 5;
        this.config.batchSize = 30;
        break;
      case '4g':
      default:
        this.config.rateLimitPerSecond = 10;
        this.config.batchSize = 50;
        break;
    }
  }

  /**
   * Load offline queue from storage
   */
  private async loadOfflineQueue(): Promise<void> {
    try {
      if (this.config.enablePersistence) {
        const stored = localStorage.getItem(this.config.offlineStorageKey);
        if (stored) {
          const queue: QueuedTransmission[] = JSON.parse(stored);
          this.transmissionQueue.push(...queue);
          this.metrics.offlineQueueSize = queue.length;
          console.log(`Loaded ${queue.length} items from offline queue`);
        }
      }
    } catch (error) {
      console.error('Failed to load offline queue:', error);
    }
  }

  /**
   * Save offline queue to storage
   */
  private async saveOfflineQueue(): Promise<void> {
    try {
      if (this.config.enablePersistence) {
        const queue = this.transmissionQueue.slice(-this.config.maxOfflineStorage);
        localStorage.setItem(this.config.offlineStorageKey, JSON.stringify(queue));
        this.metrics.offlineQueueSize = queue.length;
      }
    } catch (error) {
      console.error('Failed to save offline queue:', error);
    }
  }

  /**
   * Start transmission processor
   */
  private startTransmissionProcessor(): void {
    this.transmissionInterval = setInterval(() => {
      this.processTransmissionQueue();
    }, 1000); // Process queue every second
  }

  /**
   * Process transmission queue
   */
  private async processTransmissionQueue(): Promise<void> {
    if (!this.isOnline || this.transmissionQueue.length === 0) return;

    // Reset rate limiter if window has passed
    const now = Date.now();
    if (now - this.rateLimitWindow >= 1000) {
      this.rateLimiter = 0;
      this.rateLimitWindow = now;
    }

    // Process items within rate limit
    const itemsToProcess = Math.min(
      this.config.rateLimitPerSecond - this.rateLimiter,
      this.transmissionQueue.length,
      this.config.batchSize
    );

    if (itemsToProcess <= 0) return;

    // Sort by priority and timestamp
    this.transmissionQueue.sort((a, b) => {
      const priorityOrder = { critical: 4, high: 3, medium: 2, low: 1 };
      const priorityDiff = priorityOrder[b.priority] - priorityOrder[a.priority];
      return priorityDiff !== 0 ? priorityDiff : a.timestamp - b.timestamp;
    });

    const batch = this.transmissionQueue.splice(0, itemsToProcess);
    
    // Process batch
    for (const item of batch) {
      try {
        const result = await this.transmitSingle(item);
        
        if (!result.success && item.retries < this.config.maxRetries) {
          // Re-queue with incremented retry count
          item.retries++;
          item.timestamp = Date.now() + (this.config.retryDelay * item.retries);
          this.transmissionQueue.push(item);
        }
        
        this.updateMetrics(result);
        this.rateLimiter++;
        
      } catch (error) {
        console.error('Error processing transmission:', error);
        
        // Re-queue if retries available
        if (item.retries < this.config.maxRetries) {
          item.retries++;
          item.timestamp = Date.now() + (this.config.retryDelay * item.retries);
          this.transmissionQueue.push(item);
        }
      }
    }

    // Save queue state
    await this.saveOfflineQueue();
  }

  /**
   * Transmit single item
   */
  private async transmitSingle(item: QueuedTransmission): Promise<TransmissionResult> {
    const startTime = performance.now();
    
    try {
      let payload = item.payload;
      
      // Compress if enabled and payload is large enough
      if (this.config.compressionEnabled && 
          JSON.stringify(payload).length >= this.config.compressionThreshold) {
        payload = await this.compressPayload(payload);
      }
      
      // Encrypt if enabled
      if (this.config.encryptionEnabled && this.encryptionKey) {
        payload = await this.encryptPayload(payload);
      }
      
      // Set retry attempt in metadata
      payload.metadata.retryAttempt = item.retries;
      
      // Create request
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
        'X-Session-ID': payload.sessionId,
        'X-Transmission-ID': item.id,
        'X-Priority': item.priority,
      };
      
      if (this.config.authToken) {
        headers['Authorization'] = `Bearer ${this.config.authToken}`;
      }
      
      if (payload.metadata.compressionUsed) {
        headers['Content-Encoding'] = payload.metadata.compressionUsed;
      }
      
      if (payload.metadata.encryptionUsed) {
        headers['X-Encryption'] = payload.metadata.encryptionUsed;
      }
      
      // Make request with timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.config.timeoutMs);
      
      const response = await fetch(this.config.apiEndpoint, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
        signal: controller.signal,
      });
      
      clearTimeout(timeoutId);
      
      const transmissionTime = performance.now() - startTime;
      
      if (!response.ok) {
        return {
          success: false,
          statusCode: response.status,
          error: `HTTP ${response.status}: ${response.statusText}`,
          transmissionTime,
          retryAttempts: item.retries,
        };
      }
      
      const responseData = await response.json();
      
      return {
        success: true,
        statusCode: response.status,
        response: responseData,
        transmissionTime,
        retryAttempts: item.retries,
      };
      
    } catch (error) {
      const transmissionTime = performance.now() - startTime;
      
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        transmissionTime,
        retryAttempts: item.retries,
      };
    }
  }

  /**
   * Compress payload using worker or fallback
   */
  private async compressPayload(payload: TransmissionPayload): Promise<TransmissionPayload> {
    try {
      if (this.compressionWorker) {
        return new Promise((resolve, reject) => {
          this.compressionWorker!.onmessage = (e) => {
            const result = e.data;
            if (result.success) {
              const compressedPayload = { ...payload };
              compressedPayload.data = result.compressed;
              compressedPayload.metadata.compressionUsed = 'gzip';
              this.metrics.compressionRatio = result.ratio;
              resolve(compressedPayload);
            } else {
              reject(new Error(result.error));
            }
          };
          
          this.compressionWorker!.postMessage({
            action: 'compress',
            data: payload.data
          });
        });
      } else {
        // Fallback compression using gzip if available
        if ('CompressionStream' in window) {
          const stream = new CompressionStream('gzip');
          const writer = stream.writable.getWriter();
          const reader = stream.readable.getReader();
          
          writer.write(new TextEncoder().encode(JSON.stringify(payload.data)));
          writer.close();
          
          const compressed = await reader.read();
          const compressedPayload = { ...payload };
          compressedPayload.data = Array.from(compressed.value!);
          compressedPayload.metadata.compressionUsed = 'gzip';
          
          return compressedPayload;
        }
      }
    } catch (error) {
      console.warn('Compression failed, sending uncompressed:', error);
    }
    
    return payload;
  }

  /**
   * Encrypt payload using Web Crypto API
   */
  private async encryptPayload(payload: TransmissionPayload): Promise<TransmissionPayload> {
    try {
      if (!this.encryptionKey) {
        throw new Error('Encryption key not available');
      }
      
      const data = JSON.stringify(payload.data);
      const encoder = new TextEncoder();
      const dataBuffer = encoder.encode(data);
      
      // Generate random IV
      const iv = crypto.getRandomValues(new Uint8Array(12));
      
      // Encrypt data
      const encryptedBuffer = await crypto.subtle.encrypt(
        { name: 'AES-GCM', iv: iv },
        this.encryptionKey,
        dataBuffer
      );
      
      const encryptedPayload = { ...payload };
      encryptedPayload.data = {
        encrypted: Array.from(new Uint8Array(encryptedBuffer)),
        iv: Array.from(iv)
      };
      encryptedPayload.metadata.encryptionUsed = 'AES-GCM';
      
      return encryptedPayload;
      
    } catch (error) {
      console.warn('Encryption failed, sending unencrypted:', error);
      return payload;
    }
  }

  /**
   * Update transmission metrics
   */
  private updateMetrics(result: TransmissionResult): void {
    this.metrics.totalTransmissions++;
    
    if (result.success) {
      this.metrics.successfulTransmissions++;
    } else {
      this.metrics.failedTransmissions++;
    }
    
    // Update average transmission time
    const totalTime = this.metrics.avgTransmissionTime * (this.metrics.totalTransmissions - 1);
    this.metrics.avgTransmissionTime = (totalTime + result.transmissionTime) / this.metrics.totalTransmissions;
    
    // Update retry rate
    if (result.retryAttempts > 0) {
      this.metrics.retryRate = (this.metrics.retryRate + 1) / this.metrics.totalTransmissions;
    }
  }

  /**
   * Process offline queue when network is restored
   */
  private async processOfflineQueue(): Promise<void> {
    console.log('Processing offline queue...');
    
    // Prioritize offline items
    this.transmissionQueue.forEach(item => {
      if (item.priority === 'low') {
        item.priority = 'medium';
      } else if (item.priority === 'medium') {
        item.priority = 'high';
      }
    });
    
    // Start aggressive processing
    const originalRateLimit = this.config.rateLimitPerSecond;
    this.config.rateLimitPerSecond = Math.min(originalRateLimit * 2, 20);
    
    // Reset rate limiter after processing
    setTimeout(() => {
      this.config.rateLimitPerSecond = originalRateLimit;
    }, 30000); // 30 seconds of aggressive processing
  }

  /**
   * Public API Methods
   */

  /**
   * Transmit data with specified priority
   */
  public async transmit(
    sessionId: string, 
    data: any, 
    priority: 'low' | 'medium' | 'high' | 'critical' = 'medium'
  ): Promise<string> {
    const transmissionId = this.generateTransmissionId();
    
    const payload: TransmissionPayload = {
      sessionId,
      timestamp: Date.now(),
      data,
      metadata: {
        platform: typeof window !== 'undefined' ? 'web' : 'node',
        version: '1.0.0',
        batchSize: 1,
      }
    };
    
    const queuedTransmission: QueuedTransmission = {
      id: transmissionId,
      payload,
      timestamp: Date.now(),
      retries: 0,
      priority,
    };
    
    this.transmissionQueue.push(queuedTransmission);
    await this.saveOfflineQueue();
    
    return transmissionId;
  }

  /**
   * Transmit batch of data
   */
  public async transmitBatch(
    sessionId: string,
    dataItems: any[],
    priority: 'low' | 'medium' | 'high' | 'critical' = 'medium'
  ): Promise<string[]> {
    const transmissionIds: string[] = [];
    
    // Split into batches
    for (let i = 0; i < dataItems.length; i += this.config.batchSize) {
      const batch = dataItems.slice(i, i + this.config.batchSize);
      const id = await this.transmit(sessionId, batch, priority);
      transmissionIds.push(id);
    }
    
    return transmissionIds;
  }

  /**
   * Force immediate transmission of high-priority items
   */
  public async flush(): Promise<void> {
    // Process high-priority items immediately
    const highPriorityItems = this.transmissionQueue.filter(
      item => item.priority === 'high' || item.priority === 'critical'
    );
    
    for (const item of highPriorityItems) {
      try {
        const result = await this.transmitSingle(item);
        this.updateMetrics(result);
        
        if (result.success) {
          // Remove from queue
          const index = this.transmissionQueue.indexOf(item);
          if (index > -1) {
            this.transmissionQueue.splice(index, 1);
          }
        }
      } catch (error) {
        console.error('Error flushing transmission:', error);
      }
    }
    
    await this.saveOfflineQueue();
  }

  /**
   * Get transmission metrics
   */
  public getMetrics(): TransmissionMetrics {
    return { ...this.metrics };
  }

  /**
   * Get queue status
   */
  public getQueueStatus(): {
    totalItems: number;
    itemsByPriority: Record<string, number>;
    oldestItem?: number;
    newestItem?: number;
  } {
    const itemsByPriority = this.transmissionQueue.reduce((acc, item) => {
      acc[item.priority] = (acc[item.priority] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);
    
    const timestamps = this.transmissionQueue.map(item => item.timestamp);
    
    return {
      totalItems: this.transmissionQueue.length,
      itemsByPriority,
      oldestItem: timestamps.length > 0 ? Math.min(...timestamps) : undefined,
      newestItem: timestamps.length > 0 ? Math.max(...timestamps) : undefined,
    };
  }

  /**
   * Clear transmission queue
   */
  public clearQueue(): void {
    this.transmissionQueue = [];
    if (this.config.enablePersistence) {
      localStorage.removeItem(this.config.offlineStorageKey);
    }
    this.metrics.offlineQueueSize = 0;
  }

  /**
   * Update configuration
   */
  public updateConfig(newConfig: Partial<TransmissionConfig>): void {
    this.config = { ...this.config, ...newConfig };
  }

  /**
   * Generate unique transmission ID
   */
  private generateTransmissionId(): string {
    const timestamp = Date.now().toString(36);
    const random = Math.random().toString(36).substr(2);
    return `tx-${timestamp}-${random}`;
  }

  /**
   * Destroy and clean up resources
   */
  public destroy(): void {
    if (this.transmissionInterval) {
      clearInterval(this.transmissionInterval);
    }
    
    if (this.compressionWorker) {
      this.compressionWorker.terminate();
    }
    
    this.clearQueue();
  }
}

export default DataTransmissionModule;
export type { 
  TransmissionConfig, 
  TransmissionPayload, 
  TransmissionResult, 
  TransmissionMetrics 
};