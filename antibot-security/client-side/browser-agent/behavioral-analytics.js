/**
 * Advanced Browser Agent for Behavioral Analytics
 * Collects behavioral biometrics and device fingerprinting data
 * Optimized for sub-10ms overhead and privacy compliance
 */

class BehavioralAnalytics {
    constructor(config = {}) {
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
            ...config
        };

        this.sessionId = this.generateSessionId();
        this.events = [];
        this.deviceFingerprint = null;
        this.tlsFingerprint = null;
        this.startTime = performance.now();
        this.lastActivity = this.startTime;

        // Performance monitoring
        this.performanceMetrics = {
            eventCollectionTime: 0,
            dataTransmissionTime: 0,
            totalEvents: 0
        };

        this.init();
    }

    /**
     * Initialize the behavioral analytics system
     */
    async init() {
        try {
            // Generate device fingerprint asynchronously
            if (this.config.enableDeviceFingerprinting) {
                this.deviceFingerprint = await this.generateDeviceFingerprint();
                this.tlsFingerprint = await this.generateTLSFingerprint();
            }

            // Set up event listeners
            this.setupEventListeners();

            // Start periodic data transmission
            this.startDataTransmission();

            // Initialize performance observer
            this.setupPerformanceMonitoring();

            console.log('Behavioral Analytics initialized successfully');
        } catch (error) {
            console.error('Failed to initialize Behavioral Analytics:', error);
        }
    }

    /**
     * Generate unique session ID
     */
    generateSessionId() {
        const timestamp = Date.now().toString(36);
        const random = Math.random().toString(36).substr(2);
        return `${timestamp}-${random}`;
    }

    /**
     * Generate comprehensive device fingerprint
     */
    async generateDeviceFingerprint() {
        const fingerprint = {
            timestamp: Date.now(),
            userAgent: navigator.userAgent,
            language: navigator.language,
            languages: navigator.languages,
            platform: navigator.platform,
            cookieEnabled: navigator.cookieEnabled,
            doNotTrack: navigator.doNotTrack,
            hardwareConcurrency: navigator.hardwareConcurrency,
            maxTouchPoints: navigator.maxTouchPoints,
            memory: navigator.deviceMemory || null,
        };

        // Screen properties
        fingerprint.screen = {
            width: screen.width,
            height: screen.height,
            availWidth: screen.availWidth,
            availHeight: screen.availHeight,
            colorDepth: screen.colorDepth,
            pixelDepth: screen.pixelDepth,
            orientation: screen.orientation?.type || null
        };

        // Timezone and locale
        fingerprint.timezone = {
            offset: new Date().getTimezoneOffset(),
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            locale: Intl.DateTimeFormat().resolvedOptions().locale
        };

        // WebGL fingerprinting
        fingerprint.webgl = await this.getWebGLFingerprint();

        // Canvas fingerprinting
        fingerprint.canvas = await this.getCanvasFingerprint();

        // Audio context fingerprinting
        fingerprint.audio = await this.getAudioFingerprint();

        // Media devices
        if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
            try {
                const devices = await navigator.mediaDevices.enumerateDevices();
                fingerprint.mediaDevices = devices.map(device => ({
                    kind: device.kind,
                    deviceId: device.deviceId ? 'present' : 'absent',
                    groupId: device.groupId ? 'present' : 'absent'
                }));
            } catch (error) {
                fingerprint.mediaDevices = 'unavailable';
            }
        }

        // Network information
        if (navigator.connection) {
            fingerprint.connection = {
                effectiveType: navigator.connection.effectiveType,
                type: navigator.connection.type,
                downlink: navigator.connection.downlink,
                rtt: navigator.connection.rtt,
                saveData: navigator.connection.saveData
            };
        }

        // Generate hash of the fingerprint
        fingerprint.hash = await this.hashFingerprint(fingerprint);

        return fingerprint;
    }

    /**
     * Generate TLS fingerprint using various techniques
     */
    async generateTLSFingerprint() {
        const tlsData = {
            timestamp: Date.now(),
            supportedProtocols: [],
            cipherSuites: [],
            compression: null,
            extensions: []
        };

        // Check TLS version support
        const testUrls = [
            'https://tls-v1-0.badssl.com:1010/',
            'https://tls-v1-1.badssl.com:1011/',
            'https://tls-v1-2.badssl.com:1012/',
            'https://tls-v1-3.badssl.com:1013/'
        ];

        for (let i = 0; i < testUrls.length; i++) {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 1000);
                
                await fetch(testUrls[i], {
                    method: 'HEAD',
                    signal: controller.signal,
                    cache: 'no-cache'
                });
                
                clearTimeout(timeoutId);
                tlsData.supportedProtocols.push(`TLS 1.${i}`);
            } catch (error) {
                // Protocol not supported or error occurred
            }
        }

        return tlsData;
    }

    /**
     * Get WebGL fingerprint for device identification
     */
    async getWebGLFingerprint() {
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
                webglData.unmaskedVendor = gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL);
                webglData.unmaskedRenderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
            }

            return webglData;
        } catch (error) {
            return null;
        }
    }

    /**
     * Generate canvas fingerprint
     */
    async getCanvasFingerprint() {
        try {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            
            canvas.width = 280;
            canvas.height = 60;

            // Draw complex pattern
            ctx.textBaseline = 'top';
            ctx.font = '14px Arial';
            ctx.fillStyle = '#f60';
            ctx.fillRect(125, 1, 62, 20);
            ctx.fillStyle = '#069';
            ctx.fillText('BotDetection🤖', 2, 15);
            ctx.fillStyle = 'rgba(102, 204, 0, 0.7)';
            ctx.fillText('Canvas fingerprint', 4, 35);

            // Get image data
            const imageData = canvas.toDataURL();
            const hash = await this.simpleHash(imageData);

            return {
                dataURL: imageData.substring(0, 100) + '...', // Truncate for privacy
                hash: hash
            };
        } catch (error) {
            return null;
        }
    }

    /**
     * Generate audio context fingerprint
     */
    async getAudioFingerprint() {
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
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
    setupEventListeners() {
        if (this.config.enableMouseTracking) {
            this.setupMouseTracking();
        }

        if (this.config.enableKeyboardTracking) {
            this.setupKeyboardTracking();
        }

        if (this.config.enableScrollTracking) {
            this.setupScrollTracking();
        }

        if (this.config.enableTouchTracking) {
            this.setupTouchTracking();
        }

        // Page visibility tracking
        document.addEventListener('visibilitychange', this.handleVisibilityChange.bind(this));
        window.addEventListener('beforeunload', this.handleBeforeUnload.bind(this));
        window.addEventListener('focus', this.handleWindowFocus.bind(this));
        window.addEventListener('blur', this.handleWindowBlur.bind(this));
    }

    /**
     * Set up mouse movement and click tracking
     */
    setupMouseTracking() {
        let lastMouseEvent = 0;
        const mouseBuffer = [];

        const processMouseEvent = (event) => {
            const now = performance.now();
            if (now - lastMouseEvent < 16) return; // Throttle to ~60fps
            
            lastMouseEvent = now;
            const eventData = {
                type: 'mouse',
                subtype: event.type,
                timestamp: now,
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
                const xDiff = eventData.x - lastEvent.x;
                const yDiff = eventData.y - lastEvent.y;
                
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

        document.addEventListener('mousemove', processMouseEvent, { passive: true });
        document.addEventListener('mousedown', processMouseEvent, { passive: true });
        document.addEventListener('mouseup', processMouseEvent, { passive: true });
        document.addEventListener('click', processMouseEvent, { passive: true });
        document.addEventListener('dblclick', processMouseEvent, { passive: true });
        document.addEventListener('contextmenu', processMouseEvent, { passive: true });
    }

    /**
     * Set up keyboard event tracking
     */
    setupKeyboardTracking() {
        const keystrokeBuffer = [];

        const processKeyboardEvent = (event) => {
            const now = performance.now();
            const eventData = {
                type: 'keyboard',
                subtype: event.type,
                timestamp: now,
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
                
                if (keystrokeBuffer.length > 1) {
                    const avgDwellTime = keystrokeBuffer.slice(-5).reduce((sum, k) => sum + (k.dwellTime || 0), 0) / 5;
                    eventData.dwellTimeVariance = Math.abs(eventData.dwellTime - avgDwellTime);
                }
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
    setupScrollTracking() {
        let lastScrollEvent = 0;
        const scrollBuffer = [];

        const processScrollEvent = (event) => {
            const now = performance.now();
            if (now - lastScrollEvent < 50) return; // Throttle to 20fps for scroll
            
            lastScrollEvent = now;
            const eventData = {
                type: 'scroll',
                timestamp: now,
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
                const scrollDistance = Math.abs(eventData.scrollY - lastScroll.scrollY);
                
                eventData.scrollSpeed = scrollDistance / timeDiff;
                eventData.direction = eventData.scrollY > lastScroll.scrollY ? 'down' : 'up';
            }

            scrollBuffer.push(eventData);
            if (scrollBuffer.length > 10) scrollBuffer.shift();
            
            this.addEvent(eventData);
        };

        window.addEventListener('scroll', processScrollEvent, { passive: true });
        window.addEventListener('wheel', processScrollEvent, { passive: true });
    }

    /**
     * Set up touch event tracking for mobile devices
     */
    setupTouchTracking() {
        const processTouchEvent = (event) => {
            const now = performance.now();
            const touches = Array.from(event.touches || []).map(touch => ({
                identifier: touch.identifier,
                clientX: touch.clientX,
                clientY: touch.clientY,
                force: touch.force,
                radiusX: touch.radiusX,
                radiusY: touch.radiusY,
                rotationAngle: touch.rotationAngle
            }));

            const eventData = {
                type: 'touch',
                subtype: event.type,
                timestamp: now,
                touches: touches,
                touchCount: touches.length
            };

            this.addEvent(eventData);
        };

        document.addEventListener('touchstart', processTouchEvent, { passive: true });
        document.addEventListener('touchmove', processTouchEvent, { passive: true });
        document.addEventListener('touchend', processTouchEvent, { passive: true });
        document.addEventListener('touchcancel', processTouchEvent, { passive: true });
    }

    /**
     * Handle page visibility changes
     */
    handleVisibilityChange() {
        this.addEvent({
            type: 'visibility',
            timestamp: performance.now(),
            hidden: document.hidden,
            visibilityState: document.visibilityState
        });
    }

    /**
     * Handle before page unload
     */
    handleBeforeUnload() {
        this.flushEvents(true); // Force flush on page unload
    }

    /**
     * Handle window focus events
     */
    handleWindowFocus() {
        this.addEvent({
            type: 'focus',
            timestamp: performance.now(),
            focused: true
        });
    }

    /**
     * Handle window blur events
     */
    handleWindowBlur() {
        this.addEvent({
            type: 'focus',
            timestamp: performance.now(),
            focused: false
        });
    }

    /**
     * Add event to the buffer
     */
    addEvent(event) {
        const startTime = performance.now();
        
        event.sessionId = this.sessionId;
        event.pageUrl = window.location.href;
        event.referrer = document.referrer;
        
        this.events.push(event);
        this.lastActivity = event.timestamp;
        
        const processingTime = performance.now() - startTime;
        this.performanceMetrics.eventCollectionTime += processingTime;
        this.performanceMetrics.totalEvents++;
        
        // Auto-flush if buffer is full
        if (this.events.length >= this.config.batchSize) {
            this.flushEvents();
        }
    }

    /**
     * Start periodic data transmission
     */
    startDataTransmission() {
        setInterval(() => {
            if (this.events.length > 0) {
                this.flushEvents();
            }
        }, this.config.flushInterval);
    }

    /**
     * Flush events to the server
     */
    async flushEvents(forceSend = false) {
        if (this.events.length === 0) return;
        
        const startTime = performance.now();
        const eventsToSend = this.events.splice(0); // Clear the buffer
        
        const payload = {
            sessionId: this.sessionId,
            deviceFingerprint: this.deviceFingerprint,
            tlsFingerprint: this.tlsFingerprint,
            events: eventsToSend,
            metadata: {
                userAgent: navigator.userAgent,
                timestamp: Date.now(),
                sessionDuration: performance.now() - this.startTime,
                timeSinceLastActivity: performance.now() - this.lastActivity,
                performanceMetrics: this.performanceMetrics
            }
        };

        try {
            const response = await fetch(this.config.apiEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Session-ID': this.sessionId
                },
                body: JSON.stringify(payload),
                keepalive: forceSend // Use keepalive for page unload
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            
            const transmissionTime = performance.now() - startTime;
            this.performanceMetrics.dataTransmissionTime += transmissionTime;
            
            // Handle server response (risk score, actions, etc.)
            if (result.riskScore !== undefined) {
                this.handleRiskScore(result.riskScore, result.actions);
            }
            
        } catch (error) {
            console.error('Failed to send behavioral data:', error);
            // Re-add events to buffer for retry (implement retry logic as needed)
        }
    }

    /**
     * Handle risk score response from server
     */
    handleRiskScore(riskScore, actions = []) {
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
                    this.triggerChallenge(action.challengeType);
                    break;
                case 'block':
                    this.handleBlocked(action.reason);
                    break;
                case 'monitor':
                    this.increaseMonitoring(action.level);
                    break;
            }
        });
    }

    /**
     * Trigger challenge for user verification
     */
    triggerChallenge(challengeType) {
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
    handleBlocked(reason) {
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
    increaseMonitoring(level) {
        // Adjust collection parameters based on monitoring level
        if (level === 'high') {
            this.config.batchSize = Math.max(10, this.config.batchSize / 2);
            this.config.flushInterval = Math.max(1000, this.config.flushInterval / 2);
        }
    }

    /**
     * Set up performance monitoring
     */
    setupPerformanceMonitoring() {
        if ('PerformanceObserver' in window) {
            try {
                const observer = new PerformanceObserver((list) => {
                    const entries = list.getEntries();
                    entries.forEach(entry => {
                        if (entry.name.includes('behavioral-analytics')) {
                            this.addEvent({
                                type: 'performance',
                                timestamp: performance.now(),
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
    async simpleHash(str) {
        const encoder = new TextEncoder();
        const data = encoder.encode(str);
        const hashBuffer = await crypto.subtle.digest('SHA-256', data);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    }

    /**
     * Hash fingerprint data
     */
    async hashFingerprint(fingerprint) {
        const fingerprintString = JSON.stringify(fingerprint, Object.keys(fingerprint).sort());
        return await this.simpleHash(fingerprintString);
    }

    /**
     * Get current performance metrics
     */
    getPerformanceMetrics() {
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
     * Clean up resources
     */
    destroy() {
        this.flushEvents(true);
        // Remove event listeners if needed
        // Clear intervals
    }
}

// Export for use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = BehavioralAnalytics;
} else if (typeof window !== 'undefined') {
    window.BehavioralAnalytics = BehavioralAnalytics;
}