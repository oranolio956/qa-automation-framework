/**
 * Mobile SDK for Behavioral Analytics - React Native
 * Device fingerprinting, emulator detection, and behavioral pattern analysis
 * Cross-platform compatibility with iOS and Android
 */

import React, { useEffect, useRef, useState } from 'react';
import {
  Dimensions,
  Platform,
  DeviceInfo,
  PanResponder,
  Vibration,
  Alert,
  AppState,
  NetInfo,
  TouchableOpacity,
  View,
  Text,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import DeviceInfo from 'react-native-device-info';
import { check, request, PERMISSIONS, RESULTS } from 'react-native-permissions';
import CryptoJS from 'crypto-js';

// Type definitions
interface TouchGestureData {
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

interface BehavioralEventMobile {
  type: 'touch' | 'gesture' | 'device' | 'sensor' | 'app_state' | 'network';
  subtype?: string;
  timestamp: number;
  sessionId: string;
  data: any;
  deviceFingerprint?: string;
}

interface DeviceFingerprintMobile {
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

interface EmulatorDetectionResult {
  isEmulator: boolean;
  confidence: number;
  indicators: string[];
  riskLevel: 'low' | 'medium' | 'high';
}

interface BehavioralAnalyticsMobileConfig {
  apiEndpoint: string;
  sessionTimeout: number;
  batchSize: number;
  flushInterval: number;
  enableTouchTracking: boolean;
  enableGestureAnalysis: boolean;
  enableEmulatorDetection: boolean;
  enableSensorData: boolean;
  privacyMode: boolean;
  consentRequired: boolean;
  performanceThreshold: number;
  offlineStorageEnabled: boolean;
}

/**
 * Mobile Behavioral Analytics SDK
 * Comprehensive behavioral analysis for mobile applications
 */
class BehavioralAnalyticsMobile {
  private config: BehavioralAnalyticsMobileConfig;
  private sessionId: string;
  private events: BehavioralEventMobile[] = [];
  private deviceFingerprint: DeviceFingerprintMobile | null = null;
  private emulatorDetection: EmulatorDetectionResult | null = null;
  private touchBuffer: TouchGestureData[] = [];
  private gesturePatterns: any[] = [];
  private sensorData: any = {};
  private isInitialized: boolean = false;
  private consentGiven: boolean = false;
  private transmissionInterval: NodeJS.Timeout | null = null;
  private startTime: number = Date.now();

  constructor(config: Partial<BehavioralAnalyticsMobileConfig> = {}) {
    this.config = {
      apiEndpoint: config.apiEndpoint || 'https://api.example.com/v1/behavioral-data',
      sessionTimeout: config.sessionTimeout || 1800000, // 30 minutes
      batchSize: config.batchSize || 30,
      flushInterval: config.flushInterval || 10000, // 10 seconds
      enableTouchTracking: config.enableTouchTracking !== false,
      enableGestureAnalysis: config.enableGestureAnalysis !== false,
      enableEmulatorDetection: config.enableEmulatorDetection !== false,
      enableSensorData: config.enableSensorData !== false,
      privacyMode: config.privacyMode || false,
      consentRequired: config.consentRequired || false,
      performanceThreshold: config.performanceThreshold || 50,
      offlineStorageEnabled: config.offlineStorageEnabled !== false,
    };

    this.sessionId = this.generateSessionId();
    this.initialize();
  }

  /**
   * Initialize the mobile analytics system
   */
  private async initialize(): Promise<void> {
    try {
      const startTime = Date.now();

      // Handle consent if required
      if (this.config.consentRequired) {
        await this.handleConsentRequirement();
      } else {
        this.consentGiven = true;
      }

      if (!this.consentGiven) return;

      // Generate device fingerprint
      this.deviceFingerprint = await this.generateDeviceFingerprint();

      // Perform emulator detection
      if (this.config.enableEmulatorDetection) {
        this.emulatorDetection = await this.detectEmulator();
      }

      // Setup behavioral tracking
      this.setupBehavioralTracking();

      // Start data transmission
      this.startDataTransmission();

      // Setup app state monitoring
      this.setupAppStateMonitoring();

      const initTime = Date.now() - startTime;
      if (initTime > this.config.performanceThreshold) {
        console.warn(`Mobile analytics initialization took ${initTime}ms`);
      }

      this.isInitialized = true;
      console.log('Mobile Behavioral Analytics initialized successfully');

    } catch (error) {
      console.error('Failed to initialize Mobile Behavioral Analytics:', error);
    }
  }

  /**
   * Handle consent requirement
   */
  private async handleConsentRequirement(): Promise<void> {
    try {
      const existingConsent = await AsyncStorage.getItem('antibot-mobile-consent');
      if (existingConsent === 'granted') {
        this.consentGiven = true;
        return;
      }

      // In a real implementation, you would show a consent dialog here
      // For this example, we'll assume consent is granted
      this.consentGiven = true;
      await AsyncStorage.setItem('antibot-mobile-consent', 'granted');

    } catch (error) {
      console.error('Error handling consent:', error);
      this.consentGiven = false;
    }
  }

  /**
   * Generate unique session ID
   */
  private generateSessionId(): string {
    const timestamp = Date.now().toString(36);
    const random = Math.random().toString(36).substr(2);
    const platform = Platform.OS;
    return `${platform}-${timestamp}-${random}`;
  }

  /**
   * Generate comprehensive device fingerprint
   */
  private async generateDeviceFingerprint(): Promise<DeviceFingerprintMobile> {
    const startTime = Date.now();

    try {
      const [
        deviceId,
        model,
        brand,
        buildNumber,
        bundleId,
        deviceName,
        systemName,
        systemVersion,
        timezone,
        locale,
        isEmulator,
        isRooted,
        networkState,
        screenDimensions
      ] = await Promise.all([
        DeviceInfo.getUniqueId(),
        DeviceInfo.getModel(),
        DeviceInfo.getBrand(),
        DeviceInfo.getBuildNumber(),
        DeviceInfo.getBundleId(),
        DeviceInfo.getDeviceName(),
        DeviceInfo.getSystemName(),
        DeviceInfo.getSystemVersion(),
        DeviceInfo.getTimezone(),
        DeviceInfo.getLocales(),
        DeviceInfo.isEmulator(),
        this.detectRootedDevice(),
        NetInfo.fetch(),
        this.getScreenDimensions()
      ]);

      const fingerprint: DeviceFingerprintMobile = {
        deviceId: this.config.privacyMode ? this.hashString(deviceId) : deviceId,
        platform: Platform.OS,
        version: Platform.Version.toString(),
        model,
        brand,
        buildNumber,
        bundleId: this.config.privacyMode ? this.hashString(bundleId) : bundleId,
        deviceName: this.config.privacyMode ? 'masked' : deviceName,
        systemName,
        systemVersion,
        timezone,
        locale: Array.isArray(locale) ? locale[0]?.languageTag || 'unknown' : 'unknown',
        screenDimensions,
        networkInfo: {
          type: networkState.type || 'unknown',
          isConnected: networkState.isConnected || false,
          isInternetReachable: networkState.isInternetReachable || false,
        },
        sensors: await this.detectAvailableSensors(),
        security: {
          isEmulator,
          isRooted,
          isDebuggingEnabled: await this.detectDebugging(),
          hasMockLocation: await this.detectMockLocation(),
        },
        hash: ''
      };

      // Generate hash
      fingerprint.hash = this.hashString(JSON.stringify(fingerprint));

      const processingTime = Date.now() - startTime;
      console.log(`Device fingerprint generated in ${processingTime}ms`);

      return fingerprint;

    } catch (error) {
      console.error('Error generating device fingerprint:', error);
      throw error;
    }
  }

  /**
   * Detect if device is rooted/jailbroken
   */
  private async detectRootedDevice(): Promise<boolean> {
    try {
      if (Platform.OS === 'android') {
        return await DeviceInfo.isRooted();
      } else if (Platform.OS === 'ios') {
        return await DeviceInfo.isJailbroken();
      }
      return false;
    } catch (error) {
      console.warn('Could not detect rooted device:', error);
      return false;
    }
  }

  /**
   * Get screen dimensions and properties
   */
  private getScreenDimensions() {
    const screen = Dimensions.get('screen');
    const window = Dimensions.get('window');
    
    return {
      width: screen.width,
      height: screen.height,
      scale: screen.scale,
      fontScale: screen.fontScale,
      windowWidth: window.width,
      windowHeight: window.height,
    };
  }

  /**
   * Detect available sensors on the device
   */
  private async detectAvailableSensors(): Promise<any> {
    // This would typically use a sensor library like react-native-sensors
    // For this example, we'll simulate sensor detection
    return {
      hasAccelerometer: true,
      hasGyroscope: Platform.OS === 'ios' || Platform.Version >= 23,
      hasMagnetometer: true,
      hasBarometer: Platform.OS === 'ios',
    };
  }

  /**
   * Detect if debugging is enabled
   */
  private async detectDebugging(): Promise<boolean> {
    try {
      // On debug builds, __DEV__ is typically true
      return __DEV__ || false;
    } catch (error) {
      return false;
    }
  }

  /**
   * Detect mock location (Android primarily)
   */
  private async detectMockLocation(): Promise<boolean> {
    try {
      // This would require location permissions and specific implementation
      // For now, return false as a placeholder
      return false;
    } catch (error) {
      return false;
    }
  }

  /**
   * Comprehensive emulator detection
   */
  private async detectEmulator(): Promise<EmulatorDetectionResult> {
    const indicators: string[] = [];
    let confidence = 0;

    try {
      // Basic emulator detection
      const isEmulatorBasic = await DeviceInfo.isEmulator();
      if (isEmulatorBasic) {
        indicators.push('DeviceInfo.isEmulator() returned true');
        confidence += 0.8;
      }

      // Hardware-based detection
      const model = await DeviceInfo.getModel();
      const brand = await DeviceInfo.getBrand();
      
      // Common emulator identifiers
      const emulatorModels = ['Android SDK built for x86', 'Emulator', 'sdk_gphone', 'google_sdk'];
      const emulatorBrands = ['generic', 'Android', 'google'];
      
      if (emulatorModels.some(em => model.toLowerCase().includes(em.toLowerCase()))) {
        indicators.push(`Emulator model detected: ${model}`);
        confidence += 0.6;
      }
      
      if (emulatorBrands.some(eb => brand.toLowerCase().includes(eb.toLowerCase()))) {
        indicators.push(`Emulator brand detected: ${brand}`);
        confidence += 0.4;
      }

      // System properties detection (Android)
      if (Platform.OS === 'android') {
        const buildTags = await DeviceInfo.getBuildTags();
        if (buildTags.includes('test-keys')) {
          indicators.push('Test-keys build detected');
          confidence += 0.5;
        }
      }

      // Performance-based detection
      const screenDimensions = this.getScreenDimensions();
      if (screenDimensions.width === 1080 && screenDimensions.height === 1920) {
        // Common emulator resolution
        indicators.push('Common emulator screen resolution detected');
        confidence += 0.2;
      }

      // Network-based detection
      const networkState = await NetInfo.fetch();
      if (networkState.type === 'ethernet') {
        indicators.push('Ethernet connection on mobile device');
        confidence += 0.3;
      }

      // Temperature and battery detection (if available)
      try {
        const batteryLevel = await DeviceInfo.getBatteryLevel();
        if (batteryLevel === -1 || batteryLevel === 1.0) {
          indicators.push('Suspicious battery level');
          confidence += 0.2;
        }
      } catch (error) {
        // Battery info not available might indicate emulator
        indicators.push('Battery info unavailable');
        confidence += 0.1;
      }

      // Sensor availability check
      const sensors = await this.detectAvailableSensors();
      const sensorCount = Object.values(sensors).filter(Boolean).length;
      if (sensorCount < 2) {
        indicators.push('Limited sensor availability');
        confidence += 0.3;
      }

      // Normalize confidence to 0-1 range
      confidence = Math.min(confidence, 1.0);

      let riskLevel: 'low' | 'medium' | 'high';
      if (confidence >= 0.8) {
        riskLevel = 'high';
      } else if (confidence >= 0.5) {
        riskLevel = 'medium';
      } else {
        riskLevel = 'low';
      }

      return {
        isEmulator: confidence > 0.5,
        confidence,
        indicators,
        riskLevel
      };

    } catch (error) {
      console.error('Error in emulator detection:', error);
      return {
        isEmulator: false,
        confidence: 0,
        indicators: ['Error during detection'],
        riskLevel: 'low'
      };
    }
  }

  /**
   * Setup behavioral tracking for touches and gestures
   */
  private setupBehavioralTracking(): void {
    // This would typically be integrated with your app's touch handling
    // For React Native, you would use PanResponder or Gesture Handler
    
    if (this.config.enableTouchTracking) {
      this.setupTouchTracking();
    }

    if (this.config.enableGestureAnalysis) {
      this.setupGestureAnalysis();
    }

    if (this.config.enableSensorData) {
      this.setupSensorTracking();
    }
  }

  /**
   * Setup touch event tracking
   */
  private setupTouchTracking(): void {
    // This is a conceptual implementation
    // In practice, you would integrate this with your app's touch handlers
    
    const panResponder = PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder: () => true,
      
      onPanResponderGrant: (evt) => {
        this.handleTouchEvent('start', evt);
      },
      
      onPanResponderMove: (evt) => {
        this.handleTouchEvent('move', evt);
      },
      
      onPanResponderRelease: (evt) => {
        this.handleTouchEvent('end', evt);
      },
    });

    // Store the pan responder for later use
    (this as any).panResponder = panResponder;
  }

  /**
   * Handle touch events and calculate behavioral metrics
   */
  private handleTouchEvent(type: string, evt: any): void {
    const timestamp = Date.now();
    const touch = evt.nativeEvent;

    const touchData: TouchGestureData = {
      identifier: touch.identifier || 0,
      locationX: touch.locationX,
      locationY: touch.locationY,
      pageX: touch.pageX,
      pageY: touch.pageY,
      timestamp,
      pressure: touch.pressure,
      size: touch.size,
    };

    // Calculate velocity and acceleration
    if (this.touchBuffer.length > 0 && type === 'move') {
      const lastTouch = this.touchBuffer[this.touchBuffer.length - 1];
      const timeDiff = timestamp - lastTouch.timestamp;
      const distance = Math.sqrt(
        Math.pow(touchData.pageX - lastTouch.pageX, 2) +
        Math.pow(touchData.pageY - lastTouch.pageY, 2)
      );
      
      touchData.velocity = distance / timeDiff;
      
      if (this.touchBuffer.length > 1) {
        const prevTouch = this.touchBuffer[this.touchBuffer.length - 2];
        const prevVelocity = prevTouch.velocity || 0;
        touchData.acceleration = (touchData.velocity - prevVelocity) / timeDiff;
      }
    }

    this.touchBuffer.push(touchData);
    if (this.touchBuffer.length > 20) {
      this.touchBuffer.shift();
    }

    // Create behavioral event
    this.addEvent({
      type: 'touch',
      subtype: type,
      timestamp,
      sessionId: this.sessionId,
      data: {
        touch: touchData,
        gestureMetrics: this.calculateGestureMetrics(),
      }
    });
  }

  /**
   * Calculate gesture metrics from touch buffer
   */
  private calculateGestureMetrics(): any {
    if (this.touchBuffer.length < 2) return {};

    const velocities = this.touchBuffer
      .filter(t => t.velocity !== undefined)
      .map(t => t.velocity!);
    
    const accelerations = this.touchBuffer
      .filter(t => t.acceleration !== undefined)
      .map(t => t.acceleration!);

    return {
      avgVelocity: velocities.length > 0 ? velocities.reduce((a, b) => a + b) / velocities.length : 0,
      maxVelocity: velocities.length > 0 ? Math.max(...velocities) : 0,
      avgAcceleration: accelerations.length > 0 ? accelerations.reduce((a, b) => a + b) / accelerations.length : 0,
      touchDuration: this.touchBuffer.length > 0 ? 
        this.touchBuffer[this.touchBuffer.length - 1].timestamp - this.touchBuffer[0].timestamp : 0,
      touchPoints: this.touchBuffer.length,
    };
  }

  /**
   * Setup gesture pattern analysis
   */
  private setupGestureAnalysis(): void {
    // Analyze common gesture patterns
    setInterval(() => {
      if (this.touchBuffer.length >= 5) {
        const pattern = this.analyzeGesturePattern();
        if (pattern) {
          this.gesturePatterns.push(pattern);
          if (this.gesturePatterns.length > 10) {
            this.gesturePatterns.shift();
          }
        }
      }
    }, 1000);
  }

  /**
   * Analyze gesture patterns for bot detection
   */
  private analyzeGesturePattern(): any {
    if (this.touchBuffer.length < 5) return null;

    const recentTouches = this.touchBuffer.slice(-5);
    
    // Calculate pattern metrics
    const velocityVariation = this.calculateVariation(
      recentTouches.map(t => t.velocity || 0)
    );
    
    const pressureVariation = this.calculateVariation(
      recentTouches.map(t => t.pressure || 0.5)
    );
    
    const timingRegularity = this.calculateTimingRegularity(recentTouches);
    
    return {
      timestamp: Date.now(),
      velocityVariation,
      pressureVariation,
      timingRegularity,
      touchCount: recentTouches.length,
      isHumanLike: velocityVariation > 0.1 && pressureVariation > 0.1 && timingRegularity < 0.8,
    };
  }

  /**
   * Calculate variation in a series of values
   */
  private calculateVariation(values: number[]): number {
    if (values.length < 2) return 0;
    
    const mean = values.reduce((a, b) => a + b) / values.length;
    const variance = values.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / values.length;
    
    return Math.sqrt(variance) / (mean || 1);
  }

  /**
   * Calculate timing regularity of touches
   */
  private calculateTimingRegularity(touches: TouchGestureData[]): number {
    if (touches.length < 3) return 0;
    
    const intervals = [];
    for (let i = 1; i < touches.length; i++) {
      intervals.push(touches[i].timestamp - touches[i - 1].timestamp);
    }
    
    const avgInterval = intervals.reduce((a, b) => a + b) / intervals.length;
    const variance = intervals.reduce((sum, interval) => 
      sum + Math.pow(interval - avgInterval, 2), 0) / intervals.length;
    
    const stdDev = Math.sqrt(variance);
    return stdDev / (avgInterval || 1); // Coefficient of variation
  }

  /**
   * Setup sensor data tracking
   */
  private setupSensorTracking(): void {
    // This would typically use react-native-sensors or similar
    // For this example, we'll simulate sensor data collection
    
    setInterval(() => {
      this.collectSensorData();
    }, 5000); // Collect sensor data every 5 seconds
  }

  /**
   * Collect sensor data from device
   */
  private collectSensorData(): void {
    // Simulated sensor data - in practice this would come from actual sensors
    const sensorData = {
      accelerometer: {
        x: Math.random() * 2 - 1,
        y: Math.random() * 2 - 1,
        z: Math.random() * 2 - 1,
      },
      gyroscope: {
        x: Math.random() * 0.1 - 0.05,
        y: Math.random() * 0.1 - 0.05,
        z: Math.random() * 0.1 - 0.05,
      },
      magnetometer: {
        x: Math.random() * 100 - 50,
        y: Math.random() * 100 - 50,
        z: Math.random() * 100 - 50,
      },
    };

    this.addEvent({
      type: 'sensor',
      timestamp: Date.now(),
      sessionId: this.sessionId,
      data: sensorData,
    });
  }

  /**
   * Setup app state monitoring
   */
  private setupAppStateMonitoring(): void {
    AppState.addEventListener('change', (nextAppState) => {
      this.addEvent({
        type: 'app_state',
        timestamp: Date.now(),
        sessionId: this.sessionId,
        data: {
          state: nextAppState,
          sessionDuration: Date.now() - this.startTime,
        },
      });
    });

    // Monitor network state changes
    NetInfo.addEventListener((state) => {
      this.addEvent({
        type: 'network',
        timestamp: Date.now(),
        sessionId: this.sessionId,
        data: {
          type: state.type,
          isConnected: state.isConnected,
          isInternetReachable: state.isInternetReachable,
        },
      });
    });
  }

  /**
   * Add event to the buffer
   */
  private addEvent(event: BehavioralEventMobile): void {
    if (!this.consentGiven) return;

    event.deviceFingerprint = this.deviceFingerprint?.hash;
    this.events.push(event);

    // Auto-flush if buffer is full
    if (this.events.length >= this.config.batchSize) {
      this.flushEvents();
    }
  }

  /**
   * Start periodic data transmission
   */
  private startDataTransmission(): void {
    this.transmissionInterval = setInterval(() => {
      if (this.events.length > 0) {
        this.flushEvents();
      }
    }, this.config.flushInterval);
  }

  /**
   * Flush events to the server
   */
  private async flushEvents(): Promise<void> {
    if (this.events.length === 0) return;

    const eventsToSend = this.events.splice(0);
    
    const payload = {
      sessionId: this.sessionId,
      deviceFingerprint: this.deviceFingerprint,
      emulatorDetection: this.emulatorDetection,
      events: eventsToSend,
      metadata: {
        platform: Platform.OS,
        platformVersion: Platform.Version,
        appVersion: DeviceInfo.getVersion(),
        sessionDuration: Date.now() - this.startTime,
        timestamp: Date.now(),
        consentGiven: this.consentGiven,
        privacyMode: this.config.privacyMode,
      },
    };

    try {
      const response = await fetch(this.config.apiEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': this.sessionId,
          'X-Platform': Platform.OS,
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      this.handleServerResponse(result);

    } catch (error) {
      console.error('Failed to send mobile behavioral data:', error);
      
      // Store offline if enabled
      if (this.config.offlineStorageEnabled) {
        await this.storeOffline(payload);
      }
    }
  }

  /**
   * Handle server response
   */
  private handleServerResponse(response: any): void {
    if (response.riskScore !== undefined) {
      // Handle risk assessment
      console.log(`Risk score: ${response.riskScore}`);
      
      // Trigger appropriate actions based on risk score
      if (response.riskScore > 0.8) {
        this.triggerSecurityAlert(response);
      }
    }
  }

  /**
   * Trigger security alert for high-risk users
   */
  private triggerSecurityAlert(response: any): void {
    Alert.alert(
      'Security Notice',
      'Unusual activity detected. Please verify your identity.',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Verify', onPress: () => this.initiateVerification() },
      ]
    );
  }

  /**
   * Initiate user verification process
   */
  private initiateVerification(): void {
    // Implement verification process (biometric, SMS, etc.)
    console.log('Initiating user verification...');
  }

  /**
   * Store data offline for later transmission
   */
  private async storeOffline(payload: any): Promise<void> {
    try {
      const existingData = await AsyncStorage.getItem('antibot-offline-data');
      const offlineQueue = existingData ? JSON.parse(existingData) : [];
      
      offlineQueue.push(payload);
      
      // Limit queue size
      if (offlineQueue.length > 10) {
        offlineQueue.shift();
      }
      
      await AsyncStorage.setItem('antibot-offline-data', JSON.stringify(offlineQueue));
    } catch (error) {
      console.error('Failed to store data offline:', error);
    }
  }

  /**
   * Hash string using SHA-256
   */
  private hashString(input: string): string {
    return CryptoJS.SHA256(input).toString();
  }

  /**
   * Public API methods
   */

  /**
   * Get current session information
   */
  public getSessionInfo(): any {
    return {
      sessionId: this.sessionId,
      isInitialized: this.isInitialized,
      consentGiven: this.consentGiven,
      deviceFingerprint: this.deviceFingerprint,
      emulatorDetection: this.emulatorDetection,
      eventCount: this.events.length,
      sessionDuration: Date.now() - this.startTime,
    };
  }

  /**
   * Grant consent for data collection
   */
  public async grantConsent(): Promise<void> {
    this.consentGiven = true;
    await AsyncStorage.setItem('antibot-mobile-consent', 'granted');
    
    if (!this.isInitialized) {
      await this.initialize();
    }
  }

  /**
   * Revoke consent and stop data collection
   */
  public async revokeConsent(): Promise<void> {
    this.consentGiven = false;
    this.events = [];
    await AsyncStorage.removeItem('antibot-mobile-consent');
    
    if (this.transmissionInterval) {
      clearInterval(this.transmissionInterval);
    }
  }

  /**
   * Force flush current events
   */
  public flush(): void {
    this.flushEvents();
  }

  /**
   * Clean up resources
   */
  public destroy(): void {
    this.flushEvents();
    
    if (this.transmissionInterval) {
      clearInterval(this.transmissionInterval);
    }
    
    this.events = [];
    this.touchBuffer = [];
    this.gesturePatterns = [];
  }
}

// React Hook for easy integration
export const useBehavioralAnalytics = (config?: Partial<BehavioralAnalyticsMobileConfig>) => {
  const analyticsRef = useRef<BehavioralAnalyticsMobile | null>(null);
  const [sessionInfo, setSessionInfo] = useState<any>(null);

  useEffect(() => {
    analyticsRef.current = new BehavioralAnalyticsMobile(config);
    
    const updateSessionInfo = () => {
      if (analyticsRef.current) {
        setSessionInfo(analyticsRef.current.getSessionInfo());
      }
    };

    updateSessionInfo();
    const interval = setInterval(updateSessionInfo, 5000);

    return () => {
      clearInterval(interval);
      if (analyticsRef.current) {
        analyticsRef.current.destroy();
      }
    };
  }, []);

  const grantConsent = () => analyticsRef.current?.grantConsent();
  const revokeConsent = () => analyticsRef.current?.revokeConsent();
  const flush = () => analyticsRef.current?.flush();

  return {
    sessionInfo,
    grantConsent,
    revokeConsent,
    flush,
    analytics: analyticsRef.current,
  };
};

// React Component for consent management
export const ConsentModal: React.FC<{
  visible: boolean;
  onConsent: (granted: boolean) => void;
}> = ({ visible, onConsent }) => {
  if (!visible) return null;

  return (
    <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: 'rgba(0,0,0,0.5)' }}>
      <View style={{ backgroundColor: 'white', padding: 20, borderRadius: 10, margin: 20 }}>
        <Text style={{ fontSize: 18, fontWeight: 'bold', marginBottom: 10 }}>
          Data Collection Consent
        </Text>
        <Text style={{ marginBottom: 20 }}>
          This app collects behavioral data for security purposes. 
          This helps us detect and prevent fraudulent activity.
        </Text>
        <View style={{ flexDirection: 'row', justifyContent: 'space-around' }}>
          <TouchableOpacity 
            onPress={() => onConsent(false)}
            style={{ padding: 10, backgroundColor: '#ccc', borderRadius: 5 }}
          >
            <Text>Decline</Text>
          </TouchableOpacity>
          <TouchableOpacity 
            onPress={() => onConsent(true)}
            style={{ padding: 10, backgroundColor: '#007AFF', borderRadius: 5 }}
          >
            <Text style={{ color: 'white' }}>Accept</Text>
          </TouchableOpacity>
        </View>
      </View>
    </View>
  );
};

export default BehavioralAnalyticsMobile;