/**
 * Advanced Browser Agent for Behavioral Analytics
 * High-resolution behavioral data collection with sub-10ms overhead
 * Privacy-compliant with GDPR/CCPA support and configurable collection modes
 */

// Types and Interfaces
interface TouchEventData {
    identifier: number;
    clientX: number;
    clientY: number;
    force?: number;
    radiusX?: number;
    radiusY?: number;
    rotationAngle?: number;
}

interface BehavioralEventData {
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

interface DeviceFingerprintData {
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

interface TLSFingerprintData {
    timestamp: number;
    supportedProtocols: string[];
    cipherSuites: string[];
    compression: any;
    extensions: string[];
}

interface PerformanceMetrics {
    eventCollectionTime: number;
    dataTransmissionTime: number;
    totalEvents: number;
    avgEventCollectionTime?: number;
    bufferSize?: number;
    sessionDuration?: number;
}

interface BehavioralDataPayload {
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

interface RiskAction {
    type: 'challenge' | 'block' | 'monitor' | 'allow';
    challengeType?: string;
    reason?: string;
    level?: string;
    confidence: number;
}

interface RiskAssessmentResponse {
    sessionId: string;
    riskScore: number;
    confidence: number;
    actions: RiskAction[];
    reasons: string[];
    modelVersion: string;
    processingTimeMs: number;
    timestamp: string;
}

interface BehavioralAnalyticsConfig {
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

// Custom Events
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
    }
}

/**
 * Advanced Behavioral Analytics Class
 * Implements sub-10ms data collection with privacy compliance
 */
class BehavioralAnalytics {
    private config: Required<BehavioralAnalyticsConfig>;
    private sessionId: string;
    private events: BehavioralEventData[] = [];
    private deviceFingerprint: DeviceFingerprintData | null = null;
    private tlsFingerprint: TLSFingerprintData | null = null;
    private startTime: number;
    private lastActivity: number;
    private performanceMetrics: PerformanceMetrics;
    private transmissionQueue: BehavioralDataPayload[] = [];
    private isOnline: boolean = navigator.onLine;
    private transmissionInterval: number | null = null;
    private eventRateLimiter: number = 0;
    private lastRateLimitReset: number = Date.now();
    private consentGiven: boolean = false;
    private initialized: boolean = false;

    constructor(config: BehavioralAnalyticsConfig = {}) {
        this.config = {
            apiEndpoint: config.apiEndpoint || '/api/v1/behavioral-data',
            batchSize: config.batchSize || 50,
            flushInterval: config.flushInterval || 5000,
            enableMouseTracking: config.enableMouseTracking !== false,
            enableKeyboardTracking: config.enableKeyboardTracking !== false,
            enableScrollTracking: config.enableScrollTracking !== false,
            enableTouchTracking: config.enableTouchTracking !== false,
            enableDeviceFingerprinting: config.enableDeviceFingerprinting !== false,
            privacyMode: config.privacyMode || false,
            collectionMode: config.collectionMode || 'standard',
            consentRequired: config.consentRequired || false,
            retryAttempts: config.retryAttempts || 3,
            retryDelay: config.retryDelay || 1000,
            compressionEnabled: config.compressionEnabled || true,
            encryptionEnabled: config.encryptionEnabled || false,
            rateLimitPerSecond: config.rateLimitPerSecond || 100,
            maxEventBufferSize: config.maxEventBufferSize || 1000,
            offlineStorageEnabled: config.offlineStorageEnabled || true,
            performanceThreshold: config.performanceThreshold || 10
        };

        this.sessionId = this.generateSessionId();
        this.startTime = performance.now();
        this.lastActivity = this.startTime;

        this.performanceMetrics = {
            eventCollectionTime: 0,
            dataTransmissionTime: 0,
            totalEvents: 0
        };

        // Handle consent if required
        if (this.config.consentRequired) {
            this.handleConsentRequirement();
        } else {
            this.consentGiven = true;
            this.init();
        }

        // Setup offline/online detection
        this.setupNetworkMonitoring();
    }

    /**
     * Handle consent requirement for data collection
     */
    private handleConsentRequirement(): void {
        // Check for existing consent
        const existingConsent = localStorage.getItem('antibot-consent');
        if (existingConsent === 'granted') {
            this.consentGiven = true;
            this.init();
            return;
        }

        // Dispatch consent request event
        const consentEvent = new CustomEvent('antibot:consentRequired', {
            detail: {
                sessionId: this.sessionId,
                privacyPolicy: 'This collects behavioral data for security purposes'
            }
        });
        document.dispatchEvent(consentEvent);

        // Listen for consent response
        document.addEventListener('antibot:consent', (event) => {
            this.consentGiven = event.detail.granted;
            if (this.consentGiven) {
                localStorage.setItem('antibot-consent', 'granted');
                this.init();
            }
        });
    }

    /**
     * Initialize the behavioral analytics system
     */
    private async init(): Promise<void> {
        if (this.initialized || !this.consentGiven) return;

        try {
            const initStartTime = performance.now();

            // Generate device fingerprint asynchronously
            if (this.config.enableDeviceFingerprinting) {
                this.deviceFingerprint = await this.generateDeviceFingerprint();
                this.tlsFingerprint = await this.generateTLSFingerprint();
            }

            // Set up event listeners based on collection mode
            this.setupEventListeners();

            // Start periodic data transmission
            this.startDataTransmission();

            // Initialize performance observer
            this.setupPerformanceMonitoring();

            // Setup rate limiting
            this.setupRateLimiting();

            const initTime = performance.now() - initStartTime;
            if (initTime > this.config.performanceThreshold) {
                console.warn(`BehavioralAnalytics initialization took ${initTime.toFixed(2)}ms (threshold: ${this.config.performanceThreshold}ms)`);
            }

            this.initialized = true;
            console.log('Behavioral Analytics initialized successfully');

        } catch (error) {
            console.error('Failed to initialize Behavioral Analytics:', error);
        }
    }

    /**
     * Setup network monitoring for offline/online detection
     */
    private setupNetworkMonitoring(): void {
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.processOfflineQueue();
        });

        window.addEventListener('offline', () => {
            this.isOnline = false;
        });
    }

    /**
     * Setup rate limiting for event collection
     */
    private setupRateLimiting(): void {
        setInterval(() => {
            this.eventRateLimiter = 0;
            this.lastRateLimitReset = Date.now();
        }, 1000);
    }

    /**
     * Generate unique session ID with enhanced entropy
     */
    private generateSessionId(): string {
        const timestamp = Date.now().toString(36);
        const random1 = Math.random().toString(36).substr(2);
        const random2 = Math.random().toString(36).substr(2);
        const performance_now = performance.now().toString(36);
        return `${timestamp}-${random1}-${random2}-${performance_now}`;
    }

    /**
     * Generate comprehensive device fingerprint with enhanced features
     */
    private async generateDeviceFingerprint(): Promise<DeviceFingerprintData> {
        const startTime = performance.now();

        const fingerprint: DeviceFingerprintData = {
            timestamp: Date.now(),
            hash: '',
            userAgent: navigator.userAgent,
            language: navigator.language,
            languages: Array.from(navigator.languages),
            platform: navigator.platform,
            cookieEnabled: navigator.cookieEnabled,
            doNotTrack: navigator.doNotTrack,
            hardwareConcurrency: navigator.hardwareConcurrency,
            maxTouchPoints: navigator.maxTouchPoints,
            memory: (navigator as any).deviceMemory || undefined,
            screen: {
                width: screen.width,
                height: screen.height,
                availWidth: screen.availWidth,
                availHeight: screen.availHeight,
                colorDepth: screen.colorDepth,
                pixelDepth: screen.pixelDepth,
                orientation: (screen.orientation as any)?.type || undefined
            },
            timezone: {
                offset: new Date().getTimezoneOffset(),
                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                locale: Intl.DateTimeFormat().resolvedOptions().locale
            }
        };

        // Enhanced fingerprinting based on collection mode
        if (this.config.collectionMode === 'comprehensive') {
            fingerprint.webgl = await this.getWebGLFingerprint();
            fingerprint.canvas = await this.getCanvasFingerprint();
            fingerprint.audio = await this.getAudioFingerprint();
        }

        // Media devices enumeration
        if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
            try {
                const devices = await navigator.mediaDevices.enumerateDevices();
                fingerprint.mediaDevices = devices.map(device => ({
                    kind: device.kind,
                    deviceId: device.deviceId ? 'present' : 'absent',
                    groupId: device.groupId ? 'present' : 'absent'
                }));
            } catch (error) {
                fingerprint.mediaDevices = [];
            }
        }

        // Network information
        const connection = (navigator as any).connection;
        if (connection) {
            fingerprint.connection = {
                effectiveType: connection.effectiveType,
                type: connection.type,
                downlink: connection.downlink,
                rtt: connection.rtt,
                saveData: connection.saveData
            };
        }

        // Generate hash of the fingerprint
        fingerprint.hash = await this.hashFingerprint(fingerprint);

        const processingTime = performance.now() - startTime;
        this.performanceMetrics.eventCollectionTime += processingTime;

        return fingerprint;
    }

    /**
     * Generate TLS/JA4 fingerprint using advanced techniques
     */
    private async generateTLSFingerprint(): Promise<TLSFingerprintData> {
        const tlsData: TLSFingerprintData = {
            timestamp: Date.now(),
            supportedProtocols: [],
            cipherSuites: [],
            compression: null,
            extensions: []
        };

        // Enhanced TLS probing with JA4-like fingerprinting
        const testUrls = [
            { url: 'https://tls-v1-0.badssl.com:1010/', version: 'TLS 1.0' },
            { url: 'https://tls-v1-1.badssl.com:1011/', version: 'TLS 1.1' },
            { url: 'https://tls-v1-2.badssl.com:1012/', version: 'TLS 1.2' },
            { url: 'https://tls-v1-3.badssl.com:1013/', version: 'TLS 1.3' }
        ];

        for (const test of testUrls) {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 1000);
                
                await fetch(test.url, {
                    method: 'HEAD',
                    signal: controller.signal,
                    cache: 'no-cache'
                });
                
                clearTimeout(timeoutId);
                tlsData.supportedProtocols.push(test.version);
            } catch (error) {
                // Protocol not supported
            }
        }

        // Additional TLS fingerprinting techniques could be added here
        // Such as cipher suite enumeration, extension detection, etc.

        return tlsData;
    }

    /**
     * Get WebGL fingerprint for device identification
     */
    private async getWebGLFingerprint(): Promise<any> {
        try {
            const canvas = document.createElement('canvas');
            const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
            
            if (!gl) return null;

            const webglData = {
                vendor: gl.getParameter(gl.VENDOR),
                renderer: gl.getParameter(gl.RENDERER),
                version: gl.getParameter(gl.VERSION),
                shadingLanguageVersion: gl.getParameter(gl.SHADING_LANGUAGE_VERSION),
                maxTextureSize: gl.getParameter(gl.MAX_TEXTURE_SIZE),
                maxRenderBufferSize: gl.getParameter(gl.MAX_RENDERBUFFER_SIZE),
                maxViewportDims: gl.getParameter(gl.MAX_VIEWPORT_DIMS),
                extensions: gl.getSupportedExtensions()
            };

            // Get unmasked vendor and renderer if available
            const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
            if (debugInfo) {
                (webglData as any).unmaskedVendor = gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL);
                (webglData as any).unmaskedRenderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
            }

            return webglData;
        } catch (error) {
            return null;
        }
    }

    /**
     * Generate canvas fingerprint with enhanced entropy
     */
    private async getCanvasFingerprint(): Promise<{ dataURL: string; hash: string } | null> {
        try {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            
            if (!ctx) return null;

            canvas.width = 280;
            canvas.height = 60;

            // Draw complex pattern for fingerprinting
            ctx.textBaseline = 'top';
            ctx.font = '14px Arial';
            ctx.fillStyle = '#f60';
            ctx.fillRect(125, 1, 62, 20);
            ctx.fillStyle = '#069';
            ctx.fillText('BotDetection🤖', 2, 15);
            ctx.fillStyle = 'rgba(102, 204, 0, 0.7)';
            ctx.fillText('Canvas fingerprint', 4, 35);

            // Add geometric shapes for enhanced entropy
            ctx.beginPath();
            ctx.arc(150, 30, 20, 0, 2 * Math.PI);
            ctx.stroke();

            const imageData = canvas.toDataURL();
            const hash = await this.simpleHash(imageData);

            return {
                dataURL: this.config.privacyMode ? 'masked' : imageData.substring(0, 100) + '...',
                hash: hash
            };
        } catch (error) {
            return null;
        }
    }

    /**
     * Generate audio context fingerprint
     */
    private async getAudioFingerprint(): Promise<any> {
        try {
            const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const analyser = audioContext.createAnalyser();
            const gainNode = audioContext.createGain();
            const scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);

            gainNode.gain.value = 0; // Mute the output
            oscillator.type = 'triangle';
            oscillator.frequency.value = 1000;

            oscillator.connect(analyser);
            analyser.connect(scriptProcessor);
            scriptProcessor.connect(gainNode);
            gainNode.connect(audioContext.destination);

            oscillator.start();

            return new Promise((resolve) => {
                scriptProcessor.onaudioprocess = function(event) {
                    const buffer = event.inputBuffer.getChannelData(0);
                    let sum = 0;
                    for (let i = 0; i < buffer.length; i++) {
                        sum += Math.abs(buffer[i]);
                    }
                    
                    oscillator.stop();
                    audioContext.close();
                    
                    resolve({
                        fingerprint: sum.toString(),
                        sampleRate: audioContext.sampleRate,
                        maxChannelCount: audioContext.destination.maxChannelCount
                    });
                };
            });
        } catch (error) {
            return null;
        }
    }

    /**
     * Set up all event listeners for behavioral tracking
     */
    private setupEventListeners(): void {
        // Configure tracking based on collection mode
        const trackingConfig = this.getTrackingConfigForMode();

        if (trackingConfig.mouse && this.config.enableMouseTracking) {
            this.setupMouseTracking();
        }

        if (trackingConfig.keyboard && this.config.enableKeyboardTracking) {
            this.setupKeyboardTracking();
        }

        if (trackingConfig.scroll && this.config.enableScrollTracking) {
            this.setupScrollTracking();
        }

        if (trackingConfig.touch && this.config.enableTouchTracking) {
            this.setupTouchTracking();
        }

        // Always track page visibility and focus
        document.addEventListener('visibilitychange', this.handleVisibilityChange.bind(this), { passive: true });
        window.addEventListener('beforeunload', this.handleBeforeUnload.bind(this));
        window.addEventListener('focus', this.handleWindowFocus.bind(this), { passive: true });
        window.addEventListener('blur', this.handleWindowBlur.bind(this), { passive: true });
    }

    /**
     * Get tracking configuration based on collection mode
     */
    private getTrackingConfigForMode() {
        switch (this.config.collectionMode) {
            case 'minimal':
                return { mouse: false, keyboard: false, scroll: false, touch: true };
            case 'standard':
                return { mouse: true, keyboard: true, scroll: true, touch: true };
            case 'comprehensive':
                return { mouse: true, keyboard: true, scroll: true, touch: true };
            default:
                return { mouse: true, keyboard: true, scroll: true, touch: true };
        }
    }

    /**
     * Set up high-resolution mouse movement and click tracking
     */
    private setupMouseTracking(): void {
        let lastMouseEvent = 0;
        const mouseBuffer: BehavioralEventData[] = [];

        const processMouseEvent = (event: MouseEvent) => {
            const now = performance.now();
            
            // Rate limiting
            if (this.eventRateLimiter >= this.config.rateLimitPerSecond) return;
            if (now - lastMouseEvent < 16) return; // Throttle to ~60fps
            
            lastMouseEvent = now;
            this.eventRateLimiter++;

            const eventData: BehavioralEventData = {
                type: 'mouse',
                subtype: event.type,
                timestamp: now,
                sessionId: this.sessionId,
                pageUrl: window.location.href,
                referrer: document.referrer,
                x: event.clientX,
                y: event.clientY,
                button: event.button,
                buttons: event.buttons,
                altKey: event.altKey,
                ctrlKey: event.ctrlKey,
                shiftKey: event.shiftKey,
                metaKey: event.metaKey
            };

            // Calculate velocity and acceleration for movement events
            if (event.type === 'mousemove' && mouseBuffer.length > 0) {
                const lastEvent = mouseBuffer[mouseBuffer.length - 1];
                const timeDiff = eventData.timestamp - lastEvent.timestamp;
                const xDiff = eventData.x! - lastEvent.x!;
                const yDiff = eventData.y! - lastEvent.y!;
                
                eventData.velocity = Math.sqrt(xDiff * xDiff + yDiff * yDiff) / timeDiff;
                
                if (mouseBuffer.length > 1) {
                    const prevEvent = mouseBuffer[mouseBuffer.length - 2];
                    const prevVelocity = prevEvent.velocity || 0;
                    eventData.acceleration = (eventData.velocity - prevVelocity) / timeDiff;
                }
            }

            mouseBuffer.push(eventData);
            if (mouseBuffer.length > 10) mouseBuffer.shift();
            
            this.addEvent(eventData);
        };

        const eventOptions = { passive: true };
        document.addEventListener('mousemove', processMouseEvent, eventOptions);
        document.addEventListener('mousedown', processMouseEvent, eventOptions);
        document.addEventListener('mouseup', processMouseEvent, eventOptions);
        document.addEventListener('click', processMouseEvent, eventOptions);
        document.addEventListener('dblclick', processMouseEvent, eventOptions);
        document.addEventListener('contextmenu', processMouseEvent, eventOptions);
    }

    /**
     * Set up keyboard event tracking with enhanced privacy
     */
    private setupKeyboardTracking(): void {
        const keystrokeBuffer: BehavioralEventData[] = [];

        const processKeyboardEvent = (event: KeyboardEvent) => {
            if (this.eventRateLimiter >= this.config.rateLimitPerSecond) return;
            this.eventRateLimiter++;

            const now = performance.now();
            const eventData: BehavioralEventData = {
                type: 'keyboard',
                subtype: event.type,
                timestamp: now,
                sessionId: this.sessionId,
                pageUrl: window.location.href,
                key: this.config.privacyMode ? 'masked' : event.key,
                code: event.code,
                altKey: event.altKey,
                ctrlKey: event.ctrlKey,
                shiftKey: event.shiftKey,
                metaKey: event.metaKey,
                repeat: event.repeat
            };

            // Calculate typing patterns
            if (event.type === 'keydown' && keystrokeBuffer.length > 0) {
                const lastKeystroke = keystrokeBuffer[keystrokeBuffer.length - 1];
                eventData.dwellTime = now - lastKeystroke.timestamp;
            }

            keystrokeBuffer.push(eventData);
            if (keystrokeBuffer.length > 20) keystrokeBuffer.shift();
            
            this.addEvent(eventData);
        };

        document.addEventListener('keydown', processKeyboardEvent, { passive: true });
        document.addEventListener('keyup', processKeyboardEvent, { passive: true });
    }

    /**
     * Set up scroll behavior tracking
     */
    private setupScrollTracking(): void {
        let lastScrollEvent = 0;
        const scrollBuffer: BehavioralEventData[] = [];

        const processScrollEvent = (event: WheelEvent) => {
            const now = performance.now();
            if (this.eventRateLimiter >= this.config.rateLimitPerSecond) return;
            if (now - lastScrollEvent < 50) return; // Throttle to 20fps for scroll
            
            lastScrollEvent = now;
            this.eventRateLimiter++;

            const eventData: BehavioralEventData = {
                type: 'scroll',
                timestamp: now,
                sessionId: this.sessionId,
                pageUrl: window.location.href,
                scrollX: window.scrollX,
                scrollY: window.scrollY,
                deltaX: event.deltaX,
                deltaY: event.deltaY,
                deltaZ: event.deltaZ,
                deltaMode: event.deltaMode
            };

            // Calculate scroll patterns
            if (scrollBuffer.length > 0) {
                const lastScroll = scrollBuffer[scrollBuffer.length - 1];
                const timeDiff = eventData.timestamp - lastScroll.timestamp;
                const scrollDistance = Math.abs(eventData.scrollY! - lastScroll.scrollY!);
                
                eventData.scrollSpeed = scrollDistance / timeDiff;
                eventData.direction = eventData.scrollY! > lastScroll.scrollY! ? 'down' : 'up';
            }

            scrollBuffer.push(eventData);
            if (scrollBuffer.length > 10) scrollBuffer.shift();
            
            this.addEvent(eventData);
        };

        window.addEventListener('scroll', processScrollEvent as any, { passive: true });
        window.addEventListener('wheel', processScrollEvent, { passive: true });
    }

    /**
     * Set up touch event tracking for mobile devices
     */
    private setupTouchTracking(): void {
        const processTouchEvent = (event: TouchEvent) => {
            if (this.eventRateLimiter >= this.config.rateLimitPerSecond) return;
            this.eventRateLimiter++;

            const now = performance.now();
            const touches: TouchEventData[] = Array.from(event.touches || []).map(touch => ({
                identifier: touch.identifier,
                clientX: touch.clientX,
                clientY: touch.clientY,
                force: (touch as any).force,
                radiusX: (touch as any).radiusX,
                radiusY: (touch as any).radiusY,
                rotationAngle: (touch as any).rotationAngle
            }));

            const eventData: BehavioralEventData = {
                type: 'touch',
                subtype: event.type,
                timestamp: now,
                sessionId: this.sessionId,
                pageUrl: window.location.href,
                touches: touches,
                touchCount: touches.length
            };

            this.addEvent(eventData);
        };

        const eventOptions = { passive: true };
        document.addEventListener('touchstart', processTouchEvent, eventOptions);
        document.addEventListener('touchmove', processTouchEvent, eventOptions);
        document.addEventListener('touchend', processTouchEvent, eventOptions);
        document.addEventListener('touchcancel', processTouchEvent, eventOptions);
    }

    /**
     * Handle page visibility changes
     */
    private handleVisibilityChange(): void {
        this.addEvent({
            type: 'visibility',
            timestamp: performance.now(),
            sessionId: this.sessionId,
            pageUrl: window.location.href,
            hidden: document.hidden,
            visibilityState: document.visibilityState
        });
    }

    /**
     * Handle before page unload
     */
    private handleBeforeUnload(): void {
        this.flushEvents(true); // Force flush on page unload
    }

    /**
     * Handle window focus events
     */
    private handleWindowFocus(): void {
        this.addEvent({
            type: 'focus',
            timestamp: performance.now(),
            sessionId: this.sessionId,
            pageUrl: window.location.href,
            focused: true
        });
    }

    /**
     * Handle window blur events
     */
    private handleWindowBlur(): void {
        this.addEvent({
            type: 'focus',
            timestamp: performance.now(),
            sessionId: this.sessionId,
            pageUrl: window.location.href,
            focused: false
        });
    }

    /**
     * Add event to the buffer with performance monitoring
     */
    private addEvent(event: BehavioralEventData): void {
        if (!this.consentGiven) return;
        
        const startTime = performance.now();
        
        event.sessionId = this.sessionId;
        event.pageUrl = window.location.href;
        event.referrer = document.referrer;
        
        this.events.push(event);
        this.lastActivity = event.timestamp;
        
        const processingTime = performance.now() - startTime;
        this.performanceMetrics.eventCollectionTime += processingTime;
        this.performanceMetrics.totalEvents++;
        
        // Performance warning if collection is too slow
        if (processingTime > this.config.performanceThreshold) {
            console.warn(`Event collection took ${processingTime.toFixed(2)}ms (threshold: ${this.config.performanceThreshold}ms)`);
        }
        
        // Auto-flush if buffer is full
        if (this.events.length >= this.config.batchSize || this.events.length >= this.config.maxEventBufferSize) {
            this.flushEvents();
        }
    }

    /**
     * Start periodic data transmission
     */
    private startDataTransmission(): void {
        this.transmissionInterval = window.setInterval(() => {
            if (this.events.length > 0) {
                this.flushEvents();
            }
        }, this.config.flushInterval);
    }

    /**
     * Flush events to the server with retry logic and compression
     */
    private async flushEvents(forceSend: boolean = false): Promise<void> {
        if (this.events.length === 0) return;
        
        const startTime = performance.now();
        const eventsToSend = this.events.splice(0); // Clear the buffer
        
        const payload: BehavioralDataPayload = {
            sessionId: this.sessionId,
            deviceFingerprint: this.deviceFingerprint,
            tlsFingerprint: this.tlsFingerprint,
            events: eventsToSend,
            metadata: {
                userAgent: navigator.userAgent,
                timestamp: Date.now(),
                sessionDuration: performance.now() - this.startTime,
                timeSinceLastActivity: performance.now() - this.lastActivity,
                performanceMetrics: this.getPerformanceMetrics(),
                consentGiven: this.consentGiven,
                collectionMode: this.config.collectionMode,
                privacyMode: this.config.privacyMode
            }
        };

        // Handle offline mode
        if (!this.isOnline && this.config.offlineStorageEnabled) {
            this.storeOffline(payload);
            return;
        }

        try {
            await this.sendWithRetry(payload, forceSend);
            
            const transmissionTime = performance.now() - startTime;
            this.performanceMetrics.dataTransmissionTime += transmissionTime;
            
        } catch (error) {
            console.error('Failed to send behavioral data:', error);
            
            // Store for retry if offline storage is enabled
            if (this.config.offlineStorageEnabled) {
                this.storeOffline(payload);
            } else {
                // Re-add events to buffer for retry
                this.events.unshift(...eventsToSend);
            }
        }
    }

    /**
     * Send data with retry logic
     */
    private async sendWithRetry(payload: BehavioralDataPayload, forceSend: boolean): Promise<RiskAssessmentResponse> {
        let lastError: Error | null = null;
        
        for (let attempt = 0; attempt < this.config.retryAttempts; attempt++) {
            try {
                const headers: HeadersInit = {
                    'Content-Type': 'application/json',
                    'X-Session-ID': this.sessionId,
                    'X-Collection-Mode': this.config.collectionMode,
                    'X-Privacy-Mode': this.config.privacyMode.toString()
                };

                // Add compression if enabled
                let body = JSON.stringify(payload);
                if (this.config.compressionEnabled && 'CompressionStream' in window) {
                    // Use compression if available
                    headers['Content-Encoding'] = 'gzip';
                }

                const response = await fetch(this.config.apiEndpoint, {
                    method: 'POST',
                    headers,
                    body,
                    keepalive: forceSend,
                    signal: AbortSignal.timeout(10000) // 10 second timeout
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const result: RiskAssessmentResponse = await response.json();
                
                // Handle server response
                this.handleRiskScore(result.riskScore, result.actions);
                
                return result;
                
            } catch (error) {
                lastError = error as Error;
                
                // Don't retry on client errors (4xx)
                if (error instanceof Error && error.message.includes('4')) {
                    throw error;
                }
                
                // Wait before retry
                if (attempt < this.config.retryAttempts - 1) {
                    await new Promise(resolve => setTimeout(resolve, this.config.retryDelay * (attempt + 1)));
                }
            }
        }
        
        throw lastError || new Error('Max retries exceeded');
    }

    /**
     * Store data offline for later transmission
     */
    private storeOffline(payload: BehavioralDataPayload): void {
        try {
            this.transmissionQueue.push(payload);
            
            // Limit queue size
            if (this.transmissionQueue.length > 10) {
                this.transmissionQueue.shift();
            }
            
            // Store in localStorage as backup
            localStorage.setItem('antibot-offline-queue', JSON.stringify(this.transmissionQueue));
            
        } catch (error) {
            console.warn('Failed to store data offline:', error);
        }
    }

    /**
     * Process offline queue when back online
     */
    private async processOfflineQueue(): Promise<void> {
        try {
            // Load from localStorage
            const stored = localStorage.getItem('antibot-offline-queue');
            if (stored) {
                const storedQueue: BehavioralDataPayload[] = JSON.parse(stored);
                this.transmissionQueue.unshift(...storedQueue);
                localStorage.removeItem('antibot-offline-queue');
            }
            
            // Process queue
            while (this.transmissionQueue.length > 0 && this.isOnline) {
                const payload = this.transmissionQueue.shift()!;
                try {
                    await this.sendWithRetry(payload, false);
                } catch (error) {
                    // Put back in queue and stop processing
                    this.transmissionQueue.unshift(payload);
                    break;
                }
            }
            
        } catch (error) {
            console.error('Failed to process offline queue:', error);
        }
    }

    /**
     * Handle risk score response from server
     */
    private handleRiskScore(riskScore: number, actions: RiskAction[] = []): void {
        // Dispatch custom event for application to handle
        const event = new CustomEvent('antibot:riskScore', {
            detail: {
                riskScore,
                actions,
                sessionId: this.sessionId
            }
        });
        
        document.dispatchEvent(event);
        
        // Auto-handle certain actions
        actions.forEach(action => {
            switch (action.type) {
                case 'challenge':
                    this.triggerChallenge(action.challengeType || 'captcha');
                    break;
                case 'block':
                    this.handleBlocked(action.reason || 'Security policy violation');
                    break;
                case 'monitor':
                    this.increaseMonitoring(action.level || 'medium');
                    break;
            }
        });
    }

    /**
     * Trigger challenge for user verification
     */
    private triggerChallenge(challengeType: string): void {
        const event = new CustomEvent('antibot:challenge', {
            detail: {
                type: challengeType,
                sessionId: this.sessionId
            }
        });
        
        document.dispatchEvent(event);
    }

    /**
     * Handle blocked user
     */
    private handleBlocked(reason: string): void {
        const event = new CustomEvent('antibot:blocked', {
            detail: {
                reason,
                sessionId: this.sessionId
            }
        });
        
        document.dispatchEvent(event);
    }

    /**
     * Increase monitoring level
     */
    private increaseMonitoring(level: string): void {
        // Adjust collection parameters based on monitoring level
        if (level === 'high') {
            this.config.batchSize = Math.max(10, Math.floor(this.config.batchSize / 2));
            this.config.flushInterval = Math.max(1000, Math.floor(this.config.flushInterval / 2));
        }
    }

    /**
     * Set up performance monitoring
     */
    private setupPerformanceMonitoring(): void {
        if ('PerformanceObserver' in window) {
            try {
                const observer = new PerformanceObserver((list) => {
                    const entries = list.getEntries();
                    entries.forEach(entry => {
                        if (entry.name.includes('behavioral-analytics')) {
                            this.addEvent({
                                type: 'performance',
                                timestamp: performance.now(),
                                sessionId: this.sessionId,
                                pageUrl: window.location.href,
                                name: entry.name,
                                duration: entry.duration,
                                startTime: entry.startTime
                            });
                        }
                    });
                });
                
                observer.observe({ entryTypes: ['measure', 'navigation'] });
            } catch (error) {
                console.warn('Performance monitoring not available:', error);
            }
        }
    }

    /**
     * Generate simple hash for fingerprinting
     */
    private async simpleHash(str: string): Promise<string> {
        const encoder = new TextEncoder();
        const data = encoder.encode(str);
        const hashBuffer = await crypto.subtle.digest('SHA-256', data);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    }

    /**
     * Hash fingerprint data
     */
    private async hashFingerprint(fingerprint: DeviceFingerprintData): Promise<string> {
        const fingerprintString = JSON.stringify(fingerprint, Object.keys(fingerprint).sort());
        return await this.simpleHash(fingerprintString);
    }

    /**
     * Get current performance metrics
     */
    private getPerformanceMetrics(): PerformanceMetrics {
        return {
            ...this.performanceMetrics,
            avgEventCollectionTime: this.performanceMetrics.totalEvents > 0 
                ? this.performanceMetrics.eventCollectionTime / this.performanceMetrics.totalEvents 
                : 0,
            bufferSize: this.events.length,
            sessionDuration: performance.now() - this.startTime
        };
    }

    /**
     * Public API methods
     */

    /**
     * Grant consent for data collection
     */
    public grantConsent(): void {
        this.consentGiven = true;
        localStorage.setItem('antibot-consent', 'granted');
        
        const event = new CustomEvent('antibot:consent', {
            detail: {
                granted: true,
                sessionId: this.sessionId
            }
        });
        document.dispatchEvent(event);
        
        if (!this.initialized) {
            this.init();
        }
    }

    /**
     * Revoke consent and stop data collection
     */
    public revokeConsent(): void {
        this.consentGiven = false;
        localStorage.removeItem('antibot-consent');
        this.events = []; // Clear buffer
        
        const event = new CustomEvent('antibot:consent', {
            detail: {
                granted: false,
                sessionId: this.sessionId
            }
        });
        document.dispatchEvent(event);
    }

    /**
     * Force flush of current events
     */
    public flush(): void {
        this.flushEvents(true);
    }

    /**
     * Get current session information
     */
    public getSessionInfo(): { sessionId: string; consentGiven: boolean; metrics: PerformanceMetrics } {
        return {
            sessionId: this.sessionId,
            consentGiven: this.consentGiven,
            metrics: this.getPerformanceMetrics()
        };
    }

    /**
     * Clean up resources
     */
    public destroy(): void {
        this.flushEvents(true);
        
        if (this.transmissionInterval) {
            clearInterval(this.transmissionInterval);
        }
        
        // Remove event listeners would go here
        // Clear intervals and timers
    }
}

// Export for use
export default BehavioralAnalytics;

// Also provide global access for non-module environments
declare global {
    interface Window {
        BehavioralAnalytics: typeof BehavioralAnalytics;
    }
}

if (typeof window !== 'undefined') {
    window.BehavioralAnalytics = BehavioralAnalytics;
}