/**
 * Advanced Biometric Analytics Engine - 2025 Edition
 * Cutting-edge behavioral biometrics with keystroke dynamics, mouse trajectory patterns, and behavioral consistency scoring
 * Extends the base BehavioralAnalytics with advanced ML-grade biometric features
 */

import BehavioralAnalytics from './behavioral-analytics';

// Enhanced biometric interfaces
interface BiometricSignature {
  keystrokeDynamics?: KeystrokeDynamics;
  mouseTrajectory?: MouseTrajectoryAnalysis;
  touchPressure?: TouchPressureAnalysis;
  behavioralConsistency?: BehavioralConsistencyScore;
  temporalPattern?: TemporalPatternAnalysis;
  microBehaviors?: MicroBehaviorAnalysis;
}

interface KeystrokeDynamics {
  dwellTime: number;          // Key hold duration
  flightTime: number;         // Time between key releases
  interKeyInterval: number;   // Time between keystrokes
  typingRhythm: number;       // Rhythm consistency score
  pressureVariation: number;  // Typing pressure variation
  keyTiming: KeyTimingMetrics;
  digraphAnalysis: DigraphAnalysis[];
  trigraphAnalysis: TrigraphAnalysis[];
}

interface KeyTimingMetrics {
  averageDwellTime: number;
  dwellTimeStdDev: number;
  averageFlightTime: number;
  flightTimeStdDev: number;
  typingSpeed: number;        // WPM equivalent
  rhythmScore: number;        // 0-1, consistency metric
  pausePatterns: PausePattern[];
  correctionRate: number;     // Backspace/delete frequency
}

interface DigraphAnalysis {
  keyPair: string;           // e.g., "th", "er", "an"
  averageTiming: number;     // Average time for this key pair
  variance: number;          // Timing variance
  frequency: number;         // How often this pair occurs
}

interface TrigraphAnalysis {
  keyTriplet: string;        // e.g., "the", "and", "ing"
  averageTiming: number;
  variance: number;
  frequency: number;
}

interface PausePattern {
  duration: number;
  context: string;           // What preceded the pause
  isNatural: boolean;        // Natural vs artificial pause
  followingAction: string;   // What happened after pause
}

interface MouseTrajectoryAnalysis {
  curveComplexity: number;    // Bezier curve complexity
  velocityProfile: VelocityProfile;
  accelerationPattern: AccelerationPattern;
  microMovements: MicroMovementAnalysis;
  tremor: TremorAnalysis;
  trajectorySmoothing: number; // Natural vs artificial smoothing
  ballisticProfile: BallisticProfile;
}

interface VelocityProfile {
  peak: number;
  average: number;
  accelerationPhase: number;  // Time to reach peak velocity
  decelerationPhase: number;  // Time from peak to stop
  jerk: number;               // Rate of acceleration change
  smoothness: number;         // Velocity profile smoothness
  asymmetry: number;         // Velocity profile asymmetry
}

interface AccelerationPattern {
  initialAcceleration: number;
  peakAcceleration: number;
  accelerationJitter: number;
  ballistic: boolean;         // True ballistic movement
  subMovements: number;       // Number of corrective movements
  overshoot: number;         // Target overshoot tendency
}

interface MicroMovementAnalysis {
  count: number;              // Number of micro-movements
  amplitude: number;          // Average amplitude
  frequency: number;          // Frequency of micro-movements
  tremor: number;             // Hand tremor measurement
  precision: number;          // Movement precision score
  noiseLevel: number;        // Random movement noise
}

interface TremorAnalysis {
  frequency: number;          // Tremor frequency in Hz
  amplitude: number;          // Tremor amplitude
  consistency: number;        // Tremor pattern consistency
  isNatural: boolean;         // Natural vs. artificial tremor
  dominantAxis: 'x' | 'y' | 'both'; // Primary tremor direction
}

interface BallisticProfile {
  hasBallisticPhase: boolean; // True ballistic movement phase
  ballisticDuration: number;  // Duration of ballistic phase
  correctionPhase: number;    // Duration of correction phase
  targetAccuracy: number;     // Final positioning accuracy
}

interface TouchPressureAnalysis {
  averagePressure: number;
  pressureVariation: number;
  touchRhythm: number;
  contactArea: number;
  touchDynamics: TouchDynamics;
  multiTouchPatterns: MultiTouchPattern[];
}

interface TouchDynamics {
  approachVelocity: number;
  contactDuration: number;
  liftoffVelocity: number;
  pressureGradient: number;
  pressureRampTime: number;   // Time to reach peak pressure
  releaseTime: number;        // Time from peak to release
}

interface MultiTouchPattern {
  touchCount: number;
  averageSpacing: number;     // Distance between touch points
  symmetry: number;           // Touch pattern symmetry
  coordinationScore: number;  // Inter-finger coordination
}

interface BehavioralConsistencyScore {
  overall: number;            // Overall consistency score 0-1
  mouseConsistency: number;   // Mouse behavior consistency
  keyboardConsistency: number; // Keyboard behavior consistency
  timingConsistency: number;  // Temporal consistency
  patternDeviation: number;   // Deviation from established patterns
  humanLikelihood: number;    // Likelihood of human behavior
  adaptabilityScore: number;  // Ability to adapt to interface changes
}

interface TemporalPatternAnalysis {
  sessionRhythm: number;      // Overall session rhythm
  activityBursts: ActivityBurst[];
  pausePatterns: PausePattern[];
  circadianAlignment: number; // Alignment with expected human patterns
  fatigueSigns: FatigueIndicators;
  attentionPatterns: AttentionPattern[];
}

interface ActivityBurst {
  startTime: number;
  duration: number;
  intensity: number;
  eventTypes: string[];
  peakIntensity: number;
  energyLevel: number;
}

interface AttentionPattern {
  focusLevel: number;         // Estimated focus level
  duration: number;           // Duration of focus period
  distractionEvents: number;  // Number of distractions
  returnToFocusTime: number; // Time to regain focus
}

interface FatigueIndicators {
  typoRate: number;          // Increasing typo rate
  responseSlowing: number;    // Slowing response time
  mouseWander: number;       // Increasing mouse wandering
  attentionLapse: number;    // Attention lapse indicators
  precisionDecline: number;  // Declining movement precision
}

interface MicroBehaviorAnalysis {
  hesitationPatterns: HesitationPattern[];
  correctionBehaviors: CorrectionBehavior[];
  explorationBehaviors: ExplorationBehavior[];
  adaptationBehaviors: AdaptationBehavior[];
}

interface HesitationPattern {
  trigger: string;           // What caused the hesitation
  duration: number;          // How long the hesitation lasted
  resolution: string;        // How it was resolved
  confidence: number;        // Confidence in the final action
}

interface CorrectionBehavior {
  errorType: string;         // Type of error made
  correctionMethod: string;  // How it was corrected
  correctionTime: number;    // Time to make correction
  successRate: number;       // Success of correction
}

interface ExplorationBehavior {
  scanningSacTime: number;   // Eye scanning pattern simulation
  hoverDuration: number;     // Time spent hovering over elements
  explorationPath: string;   // Path of exploration
  decisionTime: number;      // Time to make decision
}

interface AdaptationBehavior {
  learningRate: number;      // How quickly user adapts to interface
  habitFormation: number;    // Tendency to form habits
  flexibilityScore: number;  // Adaptability to changes
  memoryRetention: number;   // Retention of learned patterns
}

interface BiometricProfile {
  keystrokeDynamics: KeystrokeDynamicsProfile;
  mouseTrajectory: MouseTrajectoryProfile;
  touchPressure: TouchPressureProfile;
  behavioralConsistency: BehavioralConsistencyProfile;
  temporalPatterns: TemporalPatternProfile;
  microBehaviors: MicroBehaviorProfile;
  overallHumanScore: number;
  confidence: number;
  uniquenessScore: number;   // How unique this profile is
  stabilityScore: number;    // How stable the patterns are
}

interface KeystrokeDynamicsProfile {
  userSignature: string;     // Unique keystroke signature
  typingStyle: 'hunt-peck' | 'touch-typing' | 'hybrid';
  skillLevel: 'beginner' | 'intermediate' | 'expert';
  dominantPatterns: string[];
  weakestPatterns: string[];
  consistencyScore: number;
}

interface MouseTrajectoryProfile {
  movementStyle: 'direct' | 'curved' | 'erratic' | 'precise';
  handedness: 'left' | 'right' | 'ambidextrous';
  dexterityLevel: number;
  preferredVelocity: number;
  accuracyScore: number;
  naturalTremor: TremorAnalysis;
}

interface TouchPressureProfile {
  touchStyle: 'light' | 'medium' | 'firm' | 'variable';
  fingerCount: number;       // Typical number of fingers used
  touchRhythm: number;
  pressureSensitivity: number;
  touchAccuracy: number;
}

interface BehavioralConsistencyProfile {
  patternStability: number;
  adaptabilityScore: number;
  behavioralEntropy: number; // Randomness in behavior
  predictabilityScore: number;
}

interface TemporalPatternProfile {
  activityLevel: 'low' | 'medium' | 'high';
  rhythmType: 'regular' | 'irregular' | 'bursts';
  peakPerformanceTime: number; // Time of day (if detectable)
  fatigueResistance: number;
}

interface MicroBehaviorProfile {
  decisionMakingSpeed: 'fast' | 'deliberate' | 'variable';
  errorRecoveryScore: number;
  explorationTendency: number;
  cautionLevel: number;
}

/**
 * Advanced Biometric Analytics Engine
 * Extends base BehavioralAnalytics with cutting-edge biometric analysis
 */
class AdvancedBiometricAnalytics extends BehavioralAnalytics {
  // Enhanced tracking arrays for biometric analysis
  private keystrokeBuffer: Array<{
    key: string;
    timestamp: number;
    duration?: number;
    pressure?: number;
    isCorrection?: boolean;
  }> = [];
  
  private mouseTrajectoryBuffer: Array<{
    x: number;
    y: number;
    timestamp: number;
    pressure?: number;
    velocity?: number;
    acceleration?: number;
  }> = [];
  
  private touchPressureBuffer: Array<{
    x: number;
    y: number;
    timestamp: number;
    pressure: number;
    area: number;
    identifier: number;
  }> = [];
  
  // Biometric analysis processors
  private keystrokeDynamicsProcessor: KeystrokeDynamicsProcessor;
  private mouseTrajectoryProcessor: MouseTrajectoryProcessor;
  private touchPressureProcessor: TouchPressureProcessor;
  private behavioralConsistencyProcessor: BehavioralConsistencyProcessor;
  private temporalPatternProcessor: TemporalPatternProcessor;
  private microBehaviorProcessor: MicroBehaviorProcessor;
  
  // Real-time biometric state
  private currentBiometricProfile: BiometricProfile | null = null;
  private profileUpdateInterval: number | null = null;
  private learningPhase: boolean = true;
  private baselineEstablished: boolean = false;
  
  constructor(config: any = {}) {
    // Initialize base class with enhanced configuration
    super({
      ...config,
      collectionMode: 'comprehensive', // Force comprehensive mode for biometrics
      enableDeviceFingerprinting: true,
      batchSize: 25, // Smaller batches for more frequent biometric updates
      flushInterval: 2500 // More frequent updates
    });
    
    // Initialize biometric processors
    this.keystrokeDynamicsProcessor = new KeystrokeDynamicsProcessor();
    this.mouseTrajectoryProcessor = new MouseTrajectoryProcessor();
    this.touchPressureProcessor = new TouchPressureProcessor();
    this.behavioralConsistencyProcessor = new BehavioralConsistencyProcessor();
    this.temporalPatternProcessor = new TemporalPatternProcessor();
    this.microBehaviorProcessor = new MicroBehaviorProcessor();
    
    this.initializeBiometricAnalysis();
  }
  
  /**
   * Initialize advanced biometric analysis
   */
  private initializeBiometricAnalysis(): void {
    // Start continuous biometric profiling
    this.startBiometricProfiling();
    
    // Enhanced event listeners for biometric data
    this.setupAdvancedEventListeners();
    
    console.log('Advanced Biometric Analytics initialized');
  }
  
  /**
   * Start continuous biometric profiling
   */
  private startBiometricProfiling(): void {
    this.profileUpdateInterval = window.setInterval(() => {
      this.updateBiometricProfile();
    }, 5000); // Update profile every 5 seconds
  }
  
  /**
   * Setup advanced event listeners for biometric analysis
   */
  private setupAdvancedEventListeners(): void {
    // Enhanced keyboard event handling
    document.addEventListener('keydown', this.handleAdvancedKeydown.bind(this), { passive: true });
    document.addEventListener('keyup', this.handleAdvancedKeyup.bind(this), { passive: true });
    
    // Enhanced mouse event handling
    document.addEventListener('mousemove', this.handleAdvancedMouseMove.bind(this), { passive: true });
    document.addEventListener('mousedown', this.handleAdvancedMouseDown.bind(this), { passive: true });
    document.addEventListener('mouseup', this.handleAdvancedMouseUp.bind(this), { passive: true });
    
    // Enhanced touch event handling
    document.addEventListener('touchstart', this.handleAdvancedTouchStart.bind(this), { passive: true });
    document.addEventListener('touchmove', this.handleAdvancedTouchMove.bind(this), { passive: true });
    document.addEventListener('touchend', this.handleAdvancedTouchEnd.bind(this), { passive: true });
    
    // Pointer events for pressure-sensitive input
    if ('PointerEvent' in window) {
      document.addEventListener('pointermove', this.handlePointerMove.bind(this), { passive: true });
      document.addEventListener('pointerdown', this.handlePointerDown.bind(this), { passive: true });
      document.addEventListener('pointerup', this.handlePointerUp.bind(this), { passive: true });
    }
  }
  
  /**
   * Enhanced keyboard event handling for keystroke dynamics
   */
  private handleAdvancedKeydown(event: KeyboardEvent): void {
    const now = performance.now();
    
    const keystroke = {
      key: event.code,
      timestamp: now,
      pressure: (event as any).pressure || 1.0,
      isCorrection: ['Backspace', 'Delete'].includes(event.code)
    };
    
    this.keystrokeBuffer.push(keystroke);
    
    // Maintain buffer size
    if (this.keystrokeBuffer.length > 200) {
      this.keystrokeBuffer = this.keystrokeBuffer.slice(-100);
    }
  }
  
  private handleAdvancedKeyup(event: KeyboardEvent): void {
    const now = performance.now();
    
    // Find corresponding keydown event
    const downEvent = this.keystrokeBuffer.find(k => 
      k.key === event.code && !k.duration
    );
    
    if (downEvent) {
      downEvent.duration = now - downEvent.timestamp;
      
      // Analyze keystroke dynamics in real-time
      const dynamics = this.keystrokeDynamicsProcessor.analyzeKeystroke(
        downEvent, 
        this.keystrokeBuffer
      );
      
      // Add biometric signature to event data
      this.addBiometricEvent('keyboard', event.code, {
        keystrokeDynamics: dynamics
      });
    }
  }
  
  /**
   * Enhanced mouse event handling for trajectory analysis
   */
  private handleAdvancedMouseMove(event: MouseEvent): void {
    const now = performance.now();
    
    const position = {
      x: event.clientX,
      y: event.clientY,
      timestamp: now,
      pressure: (event as any).pressure || 0.5
    };
    
    // Calculate velocity and acceleration
    if (this.mouseTrajectoryBuffer.length > 0) {
      const lastPos = this.mouseTrajectoryBuffer[this.mouseTrajectoryBuffer.length - 1];
      const timeDiff = now - lastPos.timestamp;
      
      if (timeDiff > 0) {
        const distance = Math.sqrt(
          Math.pow(position.x - lastPos.x, 2) + 
          Math.pow(position.y - lastPos.y, 2)
        );
        
        position.velocity = distance / timeDiff;
        
        if (lastPos.velocity !== undefined) {
          position.acceleration = (position.velocity - lastPos.velocity) / timeDiff;
        }
      }
    }
    
    this.mouseTrajectoryBuffer.push(position);
    
    // Maintain buffer size
    if (this.mouseTrajectoryBuffer.length > 500) {
      this.mouseTrajectoryBuffer = this.mouseTrajectoryBuffer.slice(-250);
    }
    
    // Analyze trajectory patterns
    if (this.mouseTrajectoryBuffer.length >= 10) {
      const trajectory = this.mouseTrajectoryProcessor.analyzeTrajectory(
        position,
        this.mouseTrajectoryBuffer.slice(-10)
      );
      
      this.addBiometricEvent('mouse', 'move', {
        mouseTrajectory: trajectory
      });
    }
  }
  
  private handleAdvancedMouseDown(event: MouseEvent): void {
    // Analyze click patterns and timing
    this.microBehaviorProcessor.analyzeClickBehavior(event, this.mouseTrajectoryBuffer);
  }
  
  private handleAdvancedMouseUp(event: MouseEvent): void {
    // Analyze release patterns
    this.microBehaviorProcessor.analyzeReleaseBehavior(event, this.mouseTrajectoryBuffer);
  }
  
  /**
   * Enhanced touch event handling for pressure analysis
   */
  private handleAdvancedTouchStart(event: TouchEvent): void {
    const now = performance.now();
    
    Array.from(event.touches).forEach(touch => {
      const touchData = {
        x: touch.clientX,
        y: touch.clientY,
        timestamp: now,
        pressure: touch.force || 0.5,
        area: (touch.radiusX || 10) * (touch.radiusY || 10),
        identifier: touch.identifier
      };
      
      this.touchPressureBuffer.push(touchData);
      
      // Analyze touch pressure patterns
      const pressureAnalysis = this.touchPressureProcessor.analyzeTouchPressure(
        touchData,
        this.touchPressureBuffer.filter(t => t.identifier === touch.identifier)
      );
      
      this.addBiometricEvent('touch', 'start', {
        touchPressure: pressureAnalysis
      });
    });
    
    // Maintain buffer size
    if (this.touchPressureBuffer.length > 300) {
      this.touchPressureBuffer = this.touchPressureBuffer.slice(-150);
    }
  }
  
  private handleAdvancedTouchMove(event: TouchEvent): void {
    // Similar to touchstart but for movement analysis
    const now = performance.now();
    
    Array.from(event.touches).forEach(touch => {
      const touchData = {
        x: touch.clientX,
        y: touch.clientY,
        timestamp: now,
        pressure: touch.force || 0.5,
        area: (touch.radiusX || 10) * (touch.radiusY || 10),
        identifier: touch.identifier
      };
      
      this.touchPressureBuffer.push(touchData);
    });
  }
  
  private handleAdvancedTouchEnd(event: TouchEvent): void {
    // Analyze touch release patterns
    Array.from(event.changedTouches).forEach(touch => {
      const touchHistory = this.touchPressureBuffer.filter(t => 
        t.identifier === touch.identifier
      );
      
      if (touchHistory.length > 0) {
        const dynamics = this.touchPressureProcessor.analyzeTouchDynamics(touchHistory);
        
        this.addBiometricEvent('touch', 'end', {
          touchPressure: {
            ...dynamics,
            touchDynamics: this.touchPressureProcessor.calculateTouchDynamics(touchHistory)
          }
        });
      }
    });
  }
  
  /**
   * Handle pointer events for pressure-sensitive input
   */
  private handlePointerMove(event: PointerEvent): void {
    // Enhanced pressure and tilt analysis for stylus input
    if (event.pointerType === 'pen') {
      const stylusData = {
        pressure: event.pressure,
        tiltX: event.tiltX,
        tiltY: event.tiltY,
        twist: event.twist,
        timestamp: performance.now(),
        x: event.clientX,
        y: event.clientY
      };
      
      this.addBiometricEvent('stylus', 'move', {
        stylusAnalysis: stylusData
      });
    }
  }
  
  private handlePointerDown(event: PointerEvent): void {
    // Analyze pen/stylus pressure patterns
    if (event.pointerType === 'pen') {
      this.microBehaviorProcessor.analyzeStylusBehavior(event);
    }
  }
  
  private handlePointerUp(event: PointerEvent): void {
    // Stylus release analysis
    if (event.pointerType === 'pen') {
      this.microBehaviorProcessor.analyzeStylusRelease(event);
    }
  }
  
  /**
   * Add biometric event with signature
   */
  private addBiometricEvent(type: string, subtype: string, biometricSignature: BiometricSignature): void {
    // This would integrate with the base class event system
    // Enhanced with biometric signature data
    const enhancedEvent = {
      type: type as any,
      subtype,
      timestamp: performance.now(),
      sessionId: this.getSessionInfo().sessionId,
      pageUrl: window.location.href,
      biometricSignature
    };
    
    // Process through base class (would need to modify base class)
    // this.addEvent(enhancedEvent);
  }
  
  /**
   * Update biometric profile based on collected data
   */
  private updateBiometricProfile(): void {
    if (this.keystrokeBuffer.length < 10 && this.mouseTrajectoryBuffer.length < 20) {
      return; // Not enough data yet
    }
    
    // Generate comprehensive biometric profile
    const profile: BiometricProfile = {
      keystrokeDynamics: this.keystrokeDynamicsProcessor.generateProfile(this.keystrokeBuffer),
      mouseTrajectory: this.mouseTrajectoryProcessor.generateProfile(this.mouseTrajectoryBuffer),
      touchPressure: this.touchPressureProcessor.generateProfile(this.touchPressureBuffer),
      behavioralConsistency: this.behavioralConsistencyProcessor.analyzeConsistency(
        this.keystrokeBuffer,
        this.mouseTrajectoryBuffer,
        this.touchPressureBuffer
      ),
      temporalPatterns: this.temporalPatternProcessor.analyzeTemporalPatterns(
        [...this.keystrokeBuffer, ...this.mouseTrajectoryBuffer]
      ),
      microBehaviors: this.microBehaviorProcessor.generateProfile(),
      overallHumanScore: 0,
      confidence: 0,
      uniquenessScore: 0,
      stabilityScore: 0
    };
    
    // Calculate composite scores
    profile.overallHumanScore = this.calculateOverallHumanScore(profile);
    profile.confidence = this.calculateProfileConfidence(profile);
    profile.uniquenessScore = this.calculateUniquenessScore(profile);
    profile.stabilityScore = this.calculateStabilityScore(profile);
    
    this.currentBiometricProfile = profile;
    
    // Check if we've established a baseline
    if (!this.baselineEstablished && profile.confidence > 0.7) {
      this.baselineEstablished = true;
      this.learningPhase = false;
      console.log('Biometric baseline established');
    }
    
    // Dispatch profile update event
    this.dispatchBiometricProfileUpdate(profile);
  }
  
  /**
   * Calculate overall human likelihood score
   */
  private calculateOverallHumanScore(profile: BiometricProfile): number {
    const scores = [
      profile.keystrokeDynamics.consistencyScore,
      profile.mouseTrajectory.accuracyScore,
      profile.touchPressure.touchAccuracy || 1,
      profile.behavioralConsistency.humanLikelihood || 0.8,
      profile.temporalPatterns.fatigueResistance || 0.7
    ].filter(score => score > 0);
    
    if (scores.length === 0) return 0.5;
    
    return scores.reduce((sum, score) => sum + score, 0) / scores.length;
  }
  
  /**
   * Calculate profile confidence based on data quality and quantity
   */
  private calculateProfileConfidence(profile: BiometricProfile): number {
    const dataPoints = this.keystrokeBuffer.length + this.mouseTrajectoryBuffer.length + this.touchPressureBuffer.length;
    
    let confidence = 0.1; // Base confidence
    
    if (dataPoints > 50) confidence = 0.3;
    if (dataPoints > 200) confidence = 0.6;
    if (dataPoints > 500) confidence = 0.8;
    if (dataPoints > 1000) confidence = 0.95;
    
    // Adjust based on behavioral consistency
    confidence *= profile.behavioralConsistency.overall;
    
    return Math.min(0.99, confidence);
  }
  
  /**
   * Calculate uniqueness score (how unique this user's patterns are)
   */
  private calculateUniquenessScore(profile: BiometricProfile): number {
    // This would typically compare against a database of known patterns
    // For now, calculate based on pattern complexity and variation
    
    const complexityFactors = [
      profile.keystrokeDynamics.typingStyle === 'touch-typing' ? 0.8 : 0.4,
      profile.mouseTrajectory.movementStyle === 'direct' ? 0.5 : 0.8,
      profile.temporalPatterns.rhythmType === 'irregular' ? 0.7 : 0.3
    ];
    
    return complexityFactors.reduce((sum, factor) => sum + factor, 0) / complexityFactors.length;
  }
  
  /**
   * Calculate stability score (how stable the patterns are over time)
   */
  private calculateStabilityScore(profile: BiometricProfile): number {
    // Compare current profile with previous profiles to measure stability
    // For now, use behavioral consistency as a proxy
    return profile.behavioralConsistency.patternStability || 0.5;
  }
  
  /**
   * Dispatch biometric profile update event
   */
  private dispatchBiometricProfileUpdate(profile: BiometricProfile): void {
    const event = new CustomEvent('antibot:biometricProfile', {
      detail: {
        profile,
        sessionId: this.getSessionInfo().sessionId,
        timestamp: Date.now(),
        learningPhase: this.learningPhase,
        baselineEstablished: this.baselineEstablished
      }
    });
    
    document.dispatchEvent(event);
  }
  
  /**
   * Public API methods
   */
  
  /**
   * Get current biometric profile
   */
  public getBiometricProfile(): BiometricProfile | null {
    return this.currentBiometricProfile;
  }
  
  /**
   * Get biometric authenticity score
   */
  public getAuthenticityScore(): number {
    if (!this.currentBiometricProfile) return 0.5;
    
    return this.currentBiometricProfile.overallHumanScore;
  }
  
  /**
   * Check if user behavior matches established baseline
   */
  public checkBehaviorAuthenticity(threshold: number = 0.8): boolean {
    if (!this.baselineEstablished || !this.currentBiometricProfile) return true;
    
    return this.currentBiometricProfile.overallHumanScore >= threshold;
  }
  
  /**
   * Force biometric profile update
   */
  public updateProfile(): void {
    this.updateBiometricProfile();
  }
  
  /**
   * Reset learning phase (use when user behavior changes significantly)
   */
  public resetLearningPhase(): void {
    this.learningPhase = true;
    this.baselineEstablished = false;
    this.keystrokeBuffer = [];
    this.mouseTrajectoryBuffer = [];
    this.touchPressureBuffer = [];
    this.currentBiometricProfile = null;
    
    console.log('Biometric learning phase reset');
  }
  
  /**
   * Export biometric data for analysis
   */
  public exportBiometricData(): any {
    return {
      profile: this.currentBiometricProfile,
      rawData: {
        keystrokes: this.keystrokeBuffer.length,
        mouseMovements: this.mouseTrajectoryBuffer.length,
        touches: this.touchPressureBuffer.length
      },
      metadata: {
        learningPhase: this.learningPhase,
        baselineEstablished: this.baselineEstablished,
        timestamp: Date.now()
      }
    };
  }
  
  /**
   * Clean up biometric analysis resources
   */
  public destroy(): void {
    if (this.profileUpdateInterval) {
      clearInterval(this.profileUpdateInterval);
    }
    
    // Clean up buffers
    this.keystrokeBuffer = [];
    this.mouseTrajectoryBuffer = [];
    this.touchPressureBuffer = [];
    
    // Call parent destroy
    super.destroy();
  }
}

// Biometric processor implementations
class KeystrokeDynamicsProcessor {
  analyzeKeystroke(keystroke: any, allKeystrokes: any[]): KeystrokeDynamics {
    const dwellTime = keystroke.duration || 100;
    const flightTime = this.calculateFlightTime(keystroke, allKeystrokes);
    const interKeyInterval = this.calculateInterKeyInterval(keystroke, allKeystrokes);
    
    return {
      dwellTime,
      flightTime,
      interKeyInterval,
      typingRhythm: this.calculateTypingRhythm(allKeystrokes),
      pressureVariation: this.calculatePressureVariation(keystroke),
      keyTiming: this.calculateKeyTiming(allKeystrokes),
      digraphAnalysis: this.analyzeDigraphs(allKeystrokes),
      trigraphAnalysis: this.analyzeTrigraphs(allKeystrokes)
    };
  }
  
  generateProfile(keystrokes: any[]): KeystrokeDynamicsProfile {
    return {
      userSignature: this.generateKeystrokeSignature(keystrokes),
      typingStyle: this.determineTypingStyle(keystrokes),
      skillLevel: this.assessSkillLevel(keystrokes),
      dominantPatterns: this.findDominantPatterns(keystrokes),
      weakestPatterns: this.findWeakestPatterns(keystrokes),
      consistencyScore: this.calculateConsistencyScore(keystrokes)
    };
  }
  
  private calculateFlightTime(keystroke: any, allKeystrokes: any[]): number {
    // Calculate flight time (time between key release and next key press)
    const currentIndex = allKeystrokes.indexOf(keystroke);
    if (currentIndex < allKeystrokes.length - 1) {
      const nextKeystroke = allKeystrokes[currentIndex + 1];
      return nextKeystroke.timestamp - (keystroke.timestamp + (keystroke.duration || 100));
    }
    return 50; // Default flight time
  }
  
  private calculateInterKeyInterval(keystroke: any, allKeystrokes: any[]): number {
    // Time between key presses
    const currentIndex = allKeystrokes.indexOf(keystroke);
    if (currentIndex > 0) {
      const prevKeystroke = allKeystrokes[currentIndex - 1];
      return keystroke.timestamp - prevKeystroke.timestamp;
    }
    return 150; // Default interval
  }
  
  private calculateTypingRhythm(allKeystrokes: any[]): number {
    if (allKeystrokes.length < 3) return 0.5;
    
    const intervals = [];
    for (let i = 1; i < allKeystrokes.length; i++) {
      intervals.push(allKeystrokes[i].timestamp - allKeystrokes[i-1].timestamp);
    }
    
    const mean = intervals.reduce((a, b) => a + b, 0) / intervals.length;
    const variance = intervals.reduce((sum, interval) => sum + Math.pow(interval - mean, 2), 0) / intervals.length;
    const cv = variance > 0 ? Math.sqrt(variance) / mean : 0;
    
    return Math.max(0, 1 - cv); // Lower coefficient of variation = higher rhythm score
  }
  
  private calculatePressureVariation(keystroke: any): number {
    return Math.abs((keystroke.pressure || 1.0) - 0.5) * 2;
  }
  
  private calculateKeyTiming(allKeystrokes: any[]): KeyTimingMetrics {
    const dwellTimes = allKeystrokes.filter(k => k.duration).map(k => k.duration);
    const avgDwell = dwellTimes.length > 0 ? dwellTimes.reduce((a, b) => a + b, 0) / dwellTimes.length : 100;
    const dwellVariance = dwellTimes.length > 0 ? dwellTimes.reduce((sum, dt) => sum + Math.pow(dt - avgDwell, 2), 0) / dwellTimes.length : 0;
    
    return {
      averageDwellTime: avgDwell,
      dwellTimeStdDev: Math.sqrt(dwellVariance),
      averageFlightTime: 80, // Simplified
      flightTimeStdDev: 20,
      typingSpeed: this.calculateTypingSpeed(allKeystrokes),
      rhythmScore: this.calculateTypingRhythm(allKeystrokes),
      pausePatterns: this.analyzePausePatterns(allKeystrokes),
      correctionRate: this.calculateCorrectionRate(allKeystrokes)
    };
  }
  
  private calculateTypingSpeed(keystrokes: any[]): number {
    if (keystrokes.length < 2) return 0;
    
    const timeSpan = keystrokes[keystrokes.length - 1].timestamp - keystrokes[0].timestamp;
    const wordsEstimate = keystrokes.length / 5; // Assume 5 characters per word
    return (wordsEstimate / (timeSpan / 60000)) || 0; // WPM
  }
  
  private analyzePausePatterns(keystrokes: any[]): PausePattern[] {
    const patterns: PausePattern[] = [];
    
    for (let i = 1; i < keystrokes.length; i++) {
      const interval = keystrokes[i].timestamp - keystrokes[i-1].timestamp;
      if (interval > 500) { // Pause longer than 500ms
        patterns.push({
          duration: interval,
          context: keystrokes[i-1].key,
          isNatural: interval < 2000, // Pauses over 2s might be artificial
          followingAction: keystrokes[i].key
        });
      }
    }
    
    return patterns;
  }
  
  private calculateCorrectionRate(keystrokes: any[]): number {
    const corrections = keystrokes.filter(k => k.isCorrection).length;
    return keystrokes.length > 0 ? corrections / keystrokes.length : 0;
  }
  
  private analyzeDigraphs(keystrokes: any[]): DigraphAnalysis[] {
    const digraphs: Map<string, number[]> = new Map();
    
    for (let i = 1; i < keystrokes.length; i++) {
      const pair = keystrokes[i-1].key + keystrokes[i].key;
      const timing = keystrokes[i].timestamp - keystrokes[i-1].timestamp;
      
      if (!digraphs.has(pair)) {
        digraphs.set(pair, []);
      }
      digraphs.get(pair)!.push(timing);
    }
    
    const analysis: DigraphAnalysis[] = [];
    digraphs.forEach((timings, pair) => {
      if (timings.length >= 3) { // Only analyze pairs that occur multiple times
        const avg = timings.reduce((a, b) => a + b, 0) / timings.length;
        const variance = timings.reduce((sum, t) => sum + Math.pow(t - avg, 2), 0) / timings.length;
        
        analysis.push({
          keyPair: pair,
          averageTiming: avg,
          variance,
          frequency: timings.length
        });
      }
    });
    
    return analysis;
  }
  
  private analyzeTrigraphs(keystrokes: any[]): TrigraphAnalysis[] {
    // Similar to digraphs but for three-key sequences
    const trigraphs: Map<string, number[]> = new Map();
    
    for (let i = 2; i < keystrokes.length; i++) {
      const triplet = keystrokes[i-2].key + keystrokes[i-1].key + keystrokes[i].key;
      const timing = keystrokes[i].timestamp - keystrokes[i-2].timestamp;
      
      if (!trigraphs.has(triplet)) {
        trigraphs.set(triplet, []);
      }
      trigraphs.get(triplet)!.push(timing);
    }
    
    const analysis: TrigraphAnalysis[] = [];
    trigraphs.forEach((timings, triplet) => {
      if (timings.length >= 2) {
        const avg = timings.reduce((a, b) => a + b, 0) / timings.length;
        const variance = timings.reduce((sum, t) => sum + Math.pow(t - avg, 2), 0) / timings.length;
        
        analysis.push({
          keyTriplet: triplet,
          averageTiming: avg,
          variance,
          frequency: timings.length
        });
      }
    });
    
    return analysis;
  }
  
  private generateKeystrokeSignature(keystrokes: any[]): string {
    // Generate a unique signature based on typing patterns
    const features = [
      this.calculateTypingSpeed(keystrokes),
      this.calculateTypingRhythm(keystrokes),
      this.calculateCorrectionRate(keystrokes)
    ];
    
    return features.map(f => Math.round(f * 100)).join('-');
  }
  
  private determineTypingStyle(keystrokes: any[]): 'hunt-peck' | 'touch-typing' | 'hybrid' {
    const avgInterval = keystrokes.length > 1 ? 
      (keystrokes[keystrokes.length-1].timestamp - keystrokes[0].timestamp) / keystrokes.length : 200;
    
    if (avgInterval > 300) return 'hunt-peck';
    if (avgInterval < 150) return 'touch-typing';
    return 'hybrid';
  }
  
  private assessSkillLevel(keystrokes: any[]): 'beginner' | 'intermediate' | 'expert' {
    const speed = this.calculateTypingSpeed(keystrokes);
    const rhythm = this.calculateTypingRhythm(keystrokes);
    
    if (speed > 60 && rhythm > 0.8) return 'expert';
    if (speed > 30 && rhythm > 0.6) return 'intermediate';
    return 'beginner';
  }
  
  private findDominantPatterns(keystrokes: any[]): string[] {
    const digraphs = this.analyzeDigraphs(keystrokes);
    return digraphs
      .sort((a, b) => b.frequency - a.frequency)
      .slice(0, 5)
      .map(d => d.keyPair);
  }
  
  private findWeakestPatterns(keystrokes: any[]): string[] {
    const digraphs = this.analyzeDigraphs(keystrokes);
    return digraphs
      .sort((a, b) => b.variance - a.variance)
      .slice(0, 3)
      .map(d => d.keyPair);
  }
  
  private calculateConsistencyScore(keystrokes: any[]): number {
    return this.calculateTypingRhythm(keystrokes);
  }
}

class MouseTrajectoryProcessor {
  analyzeTrajectory(position: any, trajectory: any[]): MouseTrajectoryAnalysis {
    return {
      curveComplexity: this.calculateCurveComplexity(trajectory),
      velocityProfile: this.analyzeVelocityProfile(trajectory),
      accelerationPattern: this.analyzeAccelerationPattern(trajectory),
      microMovements: this.analyzeMicroMovements(trajectory),
      tremor: this.analyzeTremor(trajectory),
      trajectorySmoothing: this.calculateTrajectorySmoothing(trajectory),
      ballisticProfile: this.analyzeBallisticProfile(trajectory)
    };
  }
  
  generateProfile(trajectories: any[]): MouseTrajectoryProfile {
    return {
      movementStyle: this.determineMovementStyle(trajectories),
      handedness: this.detectHandedness(trajectories),
      dexterityLevel: this.assessDexterity(trajectories),
      preferredVelocity: this.calculatePreferredVelocity(trajectories),
      accuracyScore: this.calculateAccuracyScore(trajectories),
      naturalTremor: this.analyzeTremor(trajectories)
    };
  }
  
  private calculateCurveComplexity(trajectory: any[]): number {
    if (trajectory.length < 3) return 0;
    
    let totalAngleChange = 0;
    let totalDistance = 0;
    
    for (let i = 2; i < trajectory.length; i++) {
      const p1 = trajectory[i-2];
      const p2 = trajectory[i-1];
      const p3 = trajectory[i];
      
      // Calculate vectors
      const v1 = { x: p2.x - p1.x, y: p2.y - p1.y };
      const v2 = { x: p3.x - p2.x, y: p3.y - p2.y };
      
      // Calculate angle between vectors
      const angle = Math.atan2(v2.y, v2.x) - Math.atan2(v1.y, v1.x);
      totalAngleChange += Math.abs(angle);
      
      // Calculate distance
      const distance = Math.sqrt(v1.x * v1.x + v1.y * v1.y);
      totalDistance += distance;
    }
    
    return totalDistance > 0 ? totalAngleChange / totalDistance : 0;
  }
  
  private analyzeVelocityProfile(trajectory: any[]): VelocityProfile {
    const velocities = trajectory.filter(t => t.velocity !== undefined).map(t => t.velocity);
    
    if (velocities.length === 0) {
      return {
        peak: 0,
        average: 0,
        accelerationPhase: 0,
        decelerationPhase: 0,
        jerk: 0,
        smoothness: 0,
        asymmetry: 0
      };
    }
    
    const peak = Math.max(...velocities);
    const average = velocities.reduce((a, b) => a + b, 0) / velocities.length;
    
    // Find acceleration and deceleration phases
    const peakIndex = velocities.indexOf(peak);
    const accelerationPhase = peakIndex / velocities.length;
    const decelerationPhase = (velocities.length - peakIndex) / velocities.length;
    
    // Calculate jerk (rate of acceleration change)
    let totalJerk = 0;
    for (let i = 1; i < velocities.length; i++) {
      const jerk = Math.abs(velocities[i] - velocities[i-1]);
      totalJerk += jerk;
    }
    const avgJerk = totalJerk / (velocities.length - 1);
    
    // Calculate smoothness (inverse of velocity variance)
    const variance = velocities.reduce((sum, v) => sum + Math.pow(v - average, 2), 0) / velocities.length;
    const smoothness = 1 / (1 + variance);
    
    // Calculate asymmetry
    const asymmetry = Math.abs(accelerationPhase - 0.5) * 2;
    
    return {
      peak,
      average,
      accelerationPhase,
      decelerationPhase,
      jerk: avgJerk,
      smoothness,
      asymmetry
    };
  }
  
  private analyzeAccelerationPattern(trajectory: any[]): AccelerationPattern {
    const accelerations = trajectory.filter(t => t.acceleration !== undefined).map(t => t.acceleration);
    
    if (accelerations.length === 0) {
      return {
        initialAcceleration: 0,
        peakAcceleration: 0,
        accelerationJitter: 0,
        ballistic: false,
        subMovements: 0,
        overshoot: 0
      };
    }
    
    const initial = accelerations[0] || 0;
    const peak = Math.max(...accelerations.map(a => Math.abs(a)));
    
    // Calculate jitter (variance in acceleration)
    const mean = accelerations.reduce((a, b) => a + b, 0) / accelerations.length;
    const jitter = Math.sqrt(accelerations.reduce((sum, a) => sum + Math.pow(a - mean, 2), 0) / accelerations.length);
    
    // Detect ballistic movement (initial high acceleration followed by deceleration)
    const ballistic = initial > peak * 0.7;
    
    // Count sub-movements (acceleration direction changes)
    let subMovements = 0;
    for (let i = 1; i < accelerations.length; i++) {
      if ((accelerations[i-1] > 0) !== (accelerations[i] > 0)) {
        subMovements++;
      }
    }
    
    return {
      initialAcceleration: initial,
      peakAcceleration: peak,
      accelerationJitter: jitter,
      ballistic,
      subMovements,
      overshoot: 0 // Simplified - would need target information
    };
  }
  
  private analyzeMicroMovements(trajectory: any[]): MicroMovementAnalysis {
    // Analyze small movements and corrections
    const movements = [];
    
    for (let i = 1; i < trajectory.length; i++) {
      const distance = Math.sqrt(
        Math.pow(trajectory[i].x - trajectory[i-1].x, 2) +
        Math.pow(trajectory[i].y - trajectory[i-1].y, 2)
      );
      
      if (distance < 5 && distance > 0.5) { // Micro-movement threshold
        movements.push(distance);
      }
    }
    
    const count = movements.length;
    const avgAmplitude = count > 0 ? movements.reduce((a, b) => a + b, 0) / count : 0;
    const frequency = trajectory.length > 0 ? count / trajectory.length : 0;
    
    return {
      count,
      amplitude: avgAmplitude,
      frequency,
      tremor: this.calculateTremorLevel(movements),
      precision: 1 - frequency, // Higher frequency = lower precision
      noiseLevel: this.calculateNoiseLevel(trajectory)
    };
  }
  
  private analyzeTremor(trajectory: any[]): TremorAnalysis {
    // Analyze hand tremor characteristics
    const xMovements = [];
    const yMovements = [];
    
    for (let i = 1; i < trajectory.length; i++) {
      xMovements.push(trajectory[i].x - trajectory[i-1].x);
      yMovements.push(trajectory[i].y - trajectory[i-1].y);
    }
    
    const xVariance = this.calculateVariance(xMovements);
    const yVariance = this.calculateVariance(yMovements);
    
    const frequency = this.estimateTremorFrequency(trajectory);
    const amplitude = Math.sqrt((xVariance + yVariance) / 2);
    const consistency = this.calculateTremorConsistency(trajectory);
    
    return {
      frequency,
      amplitude,
      consistency,
      isNatural: frequency >= 4 && frequency <= 12, // Natural hand tremor range
      dominantAxis: xVariance > yVariance ? 'x' : yVariance > xVariance ? 'y' : 'both'
    };
  }
  
  private calculateTrajectorySmoothing(trajectory: any[]): number {
    // Measure how smooth/artificial the trajectory appears
    if (trajectory.length < 3) return 0;
    
    let totalCurvature = 0;
    for (let i = 1; i < trajectory.length - 1; i++) {
      const curvature = this.calculatePointCurvature(
        trajectory[i-1],
        trajectory[i],
        trajectory[i+1]
      );
      totalCurvature += curvature;
    }
    
    const avgCurvature = totalCurvature / (trajectory.length - 2);
    return Math.min(1, avgCurvature); // Normalize to 0-1
  }
  
  private analyzeBallisticProfile(trajectory: any[]): BallisticProfile {
    const velocities = trajectory.filter(t => t.velocity !== undefined).map(t => t.velocity);
    
    if (velocities.length < 5) {
      return {
        hasBallisticPhase: false,
        ballisticDuration: 0,
        correctionPhase: 0,
        targetAccuracy: 0
      };
    }
    
    // Look for ballistic movement pattern (quick initial movement, then correction)
    const maxVelocity = Math.max(...velocities);
    const maxIndex = velocities.indexOf(maxVelocity);
    
    const hasBallisticPhase = maxIndex < velocities.length * 0.3; // Peak velocity in first 30%
    const ballisticDuration = hasBallisticPhase ? maxIndex / velocities.length : 0;
    const correctionPhase = hasBallisticPhase ? 1 - ballisticDuration : 0;
    
    return {
      hasBallisticPhase,
      ballisticDuration,
      correctionPhase,
      targetAccuracy: this.calculateTargetAccuracy(trajectory)
    };
  }
  
  // Helper methods for mouse trajectory analysis
  private calculateVariance(values: number[]): number {
    if (values.length === 0) return 0;
    
    const mean = values.reduce((a, b) => a + b, 0) / values.length;
    return values.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / values.length;
  }
  
  private calculateTremorLevel(movements: number[]): number {
    return this.calculateVariance(movements);
  }
  
  private calculateNoiseLevel(trajectory: any[]): number {
    // Calculate high-frequency noise in movement
    if (trajectory.length < 3) return 0;
    
    let noise = 0;
    for (let i = 1; i < trajectory.length - 1; i++) {
      const smoothed = {
        x: (trajectory[i-1].x + trajectory[i+1].x) / 2,
        y: (trajectory[i-1].y + trajectory[i+1].y) / 2
      };
      
      const actualDistance = Math.sqrt(
        Math.pow(trajectory[i].x - smoothed.x, 2) +
        Math.pow(trajectory[i].y - smoothed.y, 2)
      );
      
      noise += actualDistance;
    }
    
    return noise / (trajectory.length - 2);
  }
  
  private estimateTremorFrequency(trajectory: any[]): number {
    // Estimate tremor frequency using zero-crossing method
    if (trajectory.length < 10) return 0;
    
    const velocities = trajectory.filter(t => t.velocity !== undefined).map(t => t.velocity);
    if (velocities.length < 10) return 0;
    
    let zeroCrossings = 0;
    const mean = velocities.reduce((a, b) => a + b, 0) / velocities.length;
    
    for (let i = 1; i < velocities.length; i++) {
      if ((velocities[i-1] - mean) * (velocities[i] - mean) < 0) {
        zeroCrossings++;
      }
    }
    
    const totalTime = (trajectory[trajectory.length-1].timestamp - trajectory[0].timestamp) / 1000; // Convert to seconds
    return totalTime > 0 ? (zeroCrossings / 2) / totalTime : 0; // Hz
  }
  
  private calculateTremorConsistency(trajectory: any[]): number {
    // Measure consistency of tremor pattern
    const frequency = this.estimateTremorFrequency(trajectory);
    if (frequency === 0) return 0;
    
    // Simplified consistency calculation
    return frequency >= 4 && frequency <= 12 ? 0.8 : 0.3;
  }
  
  private calculatePointCurvature(p1: any, p2: any, p3: any): number {
    // Calculate curvature at point p2
    const v1 = { x: p2.x - p1.x, y: p2.y - p1.y };
    const v2 = { x: p3.x - p2.x, y: p3.y - p2.y };
    
    const cross = v1.x * v2.y - v1.y * v2.x;
    const v1Mag = Math.sqrt(v1.x * v1.x + v1.y * v1.y);
    const v2Mag = Math.sqrt(v2.x * v2.x + v2.y * v2.y);
    
    if (v1Mag * v2Mag === 0) return 0;
    
    return Math.abs(cross) / (v1Mag * v2Mag);
  }
  
  private calculateTargetAccuracy(trajectory: any[]): number {
    // Simplified target accuracy calculation
    // In practice, this would need target information
    return 0.8; // Placeholder
  }
  
  private determineMovementStyle(trajectories: any[]): 'direct' | 'curved' | 'erratic' | 'precise' {
    const complexity = this.calculateCurveComplexity(trajectories);
    
    if (complexity < 0.1) return 'direct';
    if (complexity < 0.3) return 'curved';
    if (complexity < 0.6) return 'precise';
    return 'erratic';
  }
  
  private detectHandedness(trajectories: any[]): 'left' | 'right' | 'ambidextrous' {
    // Analyze movement patterns to detect handedness
    // This is a simplified heuristic
    return 'right'; // Placeholder
  }
  
  private assessDexterity(trajectories: any[]): number {
    const accuracy = this.calculateAccuracyScore(trajectories);
    const smoothness = this.calculateTrajectorySmoothing(trajectories);
    
    return (accuracy + smoothness) / 2;
  }
  
  private calculatePreferredVelocity(trajectories: any[]): number {
    const velocities = trajectories.filter(t => t.velocity !== undefined).map(t => t.velocity);
    
    if (velocities.length === 0) return 0;
    
    return velocities.reduce((a, b) => a + b, 0) / velocities.length;
  }
  
  private calculateAccuracyScore(trajectories: any[]): number {
    // Calculate movement accuracy based on smoothness and efficiency
    const complexity = this.calculateCurveComplexity(trajectories);
    const smoothing = this.calculateTrajectorySmoothing(trajectories);
    
    return Math.max(0, 1 - complexity) * smoothing;
  }
}

class TouchPressureProcessor {
  analyzeTouchPressure(touch: any, touchHistory: any[]): TouchPressureAnalysis {
    return {
      averagePressure: this.calculateAveragePressure(touchHistory),
      pressureVariation: this.calculatePressureVariation(touchHistory),
      touchRhythm: this.calculateTouchRhythm(touchHistory),
      contactArea: touch.area,
      touchDynamics: this.calculateTouchDynamics(touchHistory),
      multiTouchPatterns: [] // Would be calculated for multi-touch scenarios
    };
  }
  
  analyzeTouchDynamics(touchHistory: any[]): TouchDynamics {
    if (touchHistory.length < 3) {
      return {
        approachVelocity: 0,
        contactDuration: 0,
        liftoffVelocity: 0,
        pressureGradient: 0,
        pressureRampTime: 0,
        releaseTime: 0
      };
    }
    
    const pressures = touchHistory.map(t => t.pressure);
    const maxPressure = Math.max(...pressures);
    const maxIndex = pressures.indexOf(maxPressure);
    
    return {
      approachVelocity: this.calculateApproachVelocity(touchHistory),
      contactDuration: touchHistory[touchHistory.length-1].timestamp - touchHistory[0].timestamp,
      liftoffVelocity: this.calculateLiftoffVelocity(touchHistory),
      pressureGradient: maxPressure / touchHistory.length,
      pressureRampTime: maxIndex > 0 ? touchHistory[maxIndex].timestamp - touchHistory[0].timestamp : 0,
      releaseTime: touchHistory.length - 1 - maxIndex > 0 ? 
        touchHistory[touchHistory.length-1].timestamp - touchHistory[maxIndex].timestamp : 0
    };
  }
  
  calculateTouchDynamics(touchHistory: any[]): TouchDynamics {
    return this.analyzeTouchDynamics(touchHistory);
  }
  
  generateProfile(touches: any[]): TouchPressureProfile {
    return {
      touchStyle: this.determineTouchStyle(touches),
      fingerCount: this.estimateFingerCount(touches),
      touchRhythm: this.calculateTouchRhythm(touches),
      pressureSensitivity: this.calculatePressureSensitivity(touches),
      touchAccuracy: this.calculateTouchAccuracy(touches)
    };
  }
  
  private calculateAveragePressure(touchHistory: any[]): number {
    if (touchHistory.length === 0) return 0;
    
    return touchHistory.reduce((sum, touch) => sum + touch.pressure, 0) / touchHistory.length;
  }
  
  private calculatePressureVariation(touchHistory: any[]): number {
    const avg = this.calculateAveragePressure(touchHistory);
    if (touchHistory.length === 0) return 0;
    
    const variance = touchHistory.reduce((sum, touch) => {
      return sum + Math.pow(touch.pressure - avg, 2);
    }, 0) / touchHistory.length;
    
    return Math.sqrt(variance);
  }
  
  private calculateTouchRhythm(touchHistory: any[]): number {
    if (touchHistory.length < 3) return 0.5;
    
    const intervals = [];
    for (let i = 1; i < touchHistory.length; i++) {
      intervals.push(touchHistory[i].timestamp - touchHistory[i-1].timestamp);
    }
    
    const mean = intervals.reduce((a, b) => a + b, 0) / intervals.length;
    const variance = intervals.reduce((sum, interval) => sum + Math.pow(interval - mean, 2), 0) / intervals.length;
    
    return mean > 0 ? 1 / (1 + Math.sqrt(variance) / mean) : 0.5;
  }
  
  private calculateApproachVelocity(touchHistory: any[]): number {
    if (touchHistory.length < 2) return 0;
    
    const first = touchHistory[0];
    const second = touchHistory[1];
    
    return second.pressure > first.pressure ? second.pressure - first.pressure : 0;
  }
  
  private calculateLiftoffVelocity(touchHistory: any[]): number {
    if (touchHistory.length < 2) return 0;
    
    const secondLast = touchHistory[touchHistory.length-2];
    const last = touchHistory[touchHistory.length-1];
    
    return secondLast.pressure > last.pressure ? secondLast.pressure - last.pressure : 0;
  }
  
  private determineTouchStyle(touches: any[]): 'light' | 'medium' | 'firm' | 'variable' {
    const avgPressure = this.calculateAveragePressure(touches);
    const variation = this.calculatePressureVariation(touches);
    
    if (variation > 0.3) return 'variable';
    if (avgPressure < 0.3) return 'light';
    if (avgPressure < 0.7) return 'medium';
    return 'firm';
  }
  
  private estimateFingerCount(touches: any[]): number {
    // Estimate typical number of fingers used simultaneously
    // This is simplified - would need multi-touch event analysis
    return 1;
  }
  
  private calculatePressureSensitivity(touches: any[]): number {
    return this.calculatePressureVariation(touches);
  }
  
  private calculateTouchAccuracy(touches: any[]): number {
    // Simplified accuracy calculation based on pressure consistency
    const variation = this.calculatePressureVariation(touches);
    return Math.max(0, 1 - variation);
  }
}

class BehavioralConsistencyProcessor {
  analyzeConsistency(keystrokes: any[], mouseMovements: any[], touches: any[]): BehavioralConsistencyProfile {
    return {
      patternStability: this.calculatePatternStability(keystrokes, mouseMovements),
      adaptabilityScore: this.calculateAdaptability(keystrokes, mouseMovements),
      behavioralEntropy: this.calculateBehavioralEntropy(keystrokes, mouseMovements, touches),
      predictabilityScore: this.calculatePredictability(keystrokes, mouseMovements)
    };
  }
  
  private calculatePatternStability(keystrokes: any[], mouseMovements: any[]): number {
    // Measure how stable patterns are over time
    const keystrokeStability = this.calculateKeystrokeStability(keystrokes);
    const mouseStability = this.calculateMouseStability(mouseMovements);
    
    return (keystrokeStability + mouseStability) / 2;
  }
  
  private calculateKeystrokeStability(keystrokes: any[]): number {
    if (keystrokes.length < 10) return 0.5;
    
    // Split into two halves and compare patterns
    const mid = Math.floor(keystrokes.length / 2);
    const firstHalf = keystrokes.slice(0, mid);
    const secondHalf = keystrokes.slice(mid);
    
    const firstHalfAvgInterval = this.calculateAverageInterval(firstHalf);
    const secondHalfAvgInterval = this.calculateAverageInterval(secondHalf);
    
    const difference = Math.abs(firstHalfAvgInterval - secondHalfAvgInterval);
    const average = (firstHalfAvgInterval + secondHalfAvgInterval) / 2;
    
    return average > 0 ? Math.max(0, 1 - difference / average) : 0.5;
  }
  
  private calculateMouseStability(mouseMovements: any[]): number {
    if (mouseMovements.length < 20) return 0.5;
    
    const mid = Math.floor(mouseMovements.length / 2);
    const firstHalf = mouseMovements.slice(0, mid);
    const secondHalf = mouseMovements.slice(mid);
    
    const firstHalfAvgVelocity = this.calculateAverageVelocity(firstHalf);
    const secondHalfAvgVelocity = this.calculateAverageVelocity(secondHalf);
    
    const difference = Math.abs(firstHalfAvgVelocity - secondHalfAvgVelocity);
    const average = (firstHalfAvgVelocity + secondHalfAvgVelocity) / 2;
    
    return average > 0 ? Math.max(0, 1 - difference / average) : 0.5;
  }
  
  private calculateAverageInterval(keystrokes: any[]): number {
    if (keystrokes.length < 2) return 0;
    
    let totalInterval = 0;
    for (let i = 1; i < keystrokes.length; i++) {
      totalInterval += keystrokes[i].timestamp - keystrokes[i-1].timestamp;
    }
    
    return totalInterval / (keystrokes.length - 1);
  }
  
  private calculateAverageVelocity(movements: any[]): number {
    const velocities = movements.filter(m => m.velocity !== undefined).map(m => m.velocity);
    
    if (velocities.length === 0) return 0;
    
    return velocities.reduce((sum, v) => sum + v, 0) / velocities.length;
  }
  
  private calculateAdaptability(keystrokes: any[], mouseMovements: any[]): number {
    // Measure ability to adapt to different contexts
    // This is simplified - would need more context about interface changes
    return 0.7; // Placeholder
  }
  
  private calculateBehavioralEntropy(keystrokes: any[], mouseMovements: any[], touches: any[]): number {
    // Calculate entropy (randomness) in behavior
    const keystrokeEntropy = this.calculateKeystrokeEntropy(keystrokes);
    const mouseEntropy = this.calculateMouseEntropy(mouseMovements);
    
    return (keystrokeEntropy + mouseEntropy) / 2;
  }
  
  private calculateKeystrokeEntropy(keystrokes: any[]): number {
    if (keystrokes.length === 0) return 0;
    
    // Calculate entropy of key intervals
    const intervals = [];
    for (let i = 1; i < keystrokes.length; i++) {
      intervals.push(keystrokes[i].timestamp - keystrokes[i-1].timestamp);
    }
    
    return this.calculateEntropy(intervals);
  }
  
  private calculateMouseEntropy(mouseMovements: any[]): number {
    const velocities = mouseMovements.filter(m => m.velocity !== undefined).map(m => m.velocity);
    
    if (velocities.length === 0) return 0;
    
    return this.calculateEntropy(velocities);
  }
  
  private calculateEntropy(values: number[]): number {
    if (values.length === 0) return 0;
    
    // Discretize values into bins
    const bins = 10;
    const min = Math.min(...values);
    const max = Math.max(...values);
    const binSize = (max - min) / bins;
    
    const histogram = new Array(bins).fill(0);
    
    values.forEach(value => {
      const bin = Math.floor((value - min) / binSize);
      const clampedBin = Math.max(0, Math.min(bins - 1, bin));
      histogram[clampedBin]++;
    });
    
    // Calculate entropy
    let entropy = 0;
    const total = values.length;
    
    histogram.forEach(count => {
      if (count > 0) {
        const probability = count / total;
        entropy -= probability * Math.log2(probability);
      }
    });
    
    return entropy / Math.log2(bins); // Normalize to 0-1
  }
  
  private calculatePredictability(keystrokes: any[], mouseMovements: any[]): number {
    // Inverse of entropy
    const entropy = this.calculateBehavioralEntropy(keystrokes, mouseMovements, []);
    return 1 - entropy;
  }
}

class TemporalPatternProcessor {
  analyzeTemporalPatterns(events: any[]): TemporalPatternProfile {
    return {
      activityLevel: this.determineActivityLevel(events),
      rhythmType: this.determineRhythmType(events),
      peakPerformanceTime: this.estimatePeakPerformanceTime(events),
      fatigueResistance: this.calculateFatigueResistance(events)
    };
  }
  
  private determineActivityLevel(events: any[]): 'low' | 'medium' | 'high' {
    if (events.length === 0) return 'low';
    
    const duration = events[events.length-1].timestamp - events[0].timestamp;
    const eventsPerSecond = events.length / (duration / 1000);
    
    if (eventsPerSecond < 1) return 'low';
    if (eventsPerSecond < 3) return 'medium';
    return 'high';
  }
  
  private determineRhythmType(events: any[]): 'regular' | 'irregular' | 'bursts' {
    if (events.length < 5) return 'irregular';
    
    const intervals = [];
    for (let i = 1; i < events.length; i++) {
      intervals.push(events[i].timestamp - events[i-1].timestamp);
    }
    
    const mean = intervals.reduce((a, b) => a + b, 0) / intervals.length;
    const variance = intervals.reduce((sum, interval) => sum + Math.pow(interval - mean, 2), 0) / intervals.length;
    const cv = Math.sqrt(variance) / mean;
    
    if (cv < 0.3) return 'regular';
    if (cv > 1.0) return 'bursts';
    return 'irregular';
  }
  
  private estimatePeakPerformanceTime(events: any[]): number {
    // This would typically analyze time-of-day patterns
    // For now, return current hour as placeholder
    return new Date().getHours();
  }
  
  private calculateFatigueResistance(events: any[]): number {
    // Measure how performance degrades over time
    if (events.length < 20) return 0.7;
    
    const firstQuarter = events.slice(0, Math.floor(events.length / 4));
    const lastQuarter = events.slice(-Math.floor(events.length / 4));
    
    const firstQuarterActivity = this.calculateActivityRate(firstQuarter);
    const lastQuarterActivity = this.calculateActivityRate(lastQuarter);
    
    if (firstQuarterActivity === 0) return 0.5;
    
    const fatigueRatio = lastQuarterActivity / firstQuarterActivity;
    return Math.min(1, fatigueRatio); // Higher ratio = better fatigue resistance
  }
  
  private calculateActivityRate(events: any[]): number {
    if (events.length < 2) return 0;
    
    const duration = events[events.length-1].timestamp - events[0].timestamp;
    return duration > 0 ? events.length / (duration / 1000) : 0;
  }
}

class MicroBehaviorProcessor {
  private hesitations: HesitationPattern[] = [];
  private corrections: CorrectionBehavior[] = [];
  
  analyzeClickBehavior(event: MouseEvent, trajectory: any[]): void {
    // Analyze hesitation before click
    const dwellTime = this.calculateDwellTimeBeforeClick(event, trajectory);
    
    if (dwellTime > 500) { // Hesitation threshold
      this.hesitations.push({
        trigger: 'click_decision',
        duration: dwellTime,
        resolution: 'clicked',
        confidence: dwellTime > 2000 ? 0.3 : 0.7
      });
    }
  }
  
  analyzeReleaseBehavior(event: MouseEvent, trajectory: any[]): void {
    // Analyze release patterns
    const releaseSpeed = this.calculateReleaseSpeed(event, trajectory);
    
    if (releaseSpeed < 0.1) {
      this.hesitations.push({
        trigger: 'release_decision',
        duration: 100,
        resolution: 'released',
        confidence: 0.8
      });
    }
  }
  
  analyzeStylusBehavior(event: PointerEvent): void {
    // Analyze stylus-specific behaviors
  }
  
  analyzeStylusRelease(event: PointerEvent): void {
    // Analyze stylus release patterns
  }
  
  generateProfile(): MicroBehaviorProfile {
    return {
      decisionMakingSpeed: this.determineDecisionMakingSpeed(),
      errorRecoveryScore: this.calculateErrorRecoveryScore(),
      explorationTendency: this.calculateExplorationTendency(),
      cautionLevel: this.calculateCautionLevel()
    };
  }
  
  private calculateDwellTimeBeforeClick(event: MouseEvent, trajectory: any[]): number {
    // Calculate how long mouse was near click position
    const clickPos = { x: event.clientX, y: event.clientY };
    const threshold = 20; // pixels
    
    let dwellTime = 0;
    for (let i = trajectory.length - 1; i >= 0; i--) {
      const pos = trajectory[i];
      const distance = Math.sqrt(
        Math.pow(clickPos.x - pos.x, 2) + Math.pow(clickPos.y - pos.y, 2)
      );
      
      if (distance <= threshold) {
        dwellTime = event.timeStamp - pos.timestamp;
      } else {
        break;
      }
    }
    
    return dwellTime;
  }
  
  private calculateReleaseSpeed(event: MouseEvent, trajectory: any[]): number {
    // Calculate how quickly mouse moved after release
    // This is simplified - would need post-release tracking
    return 0.5; // Placeholder
  }
  
  private determineDecisionMakingSpeed(): 'fast' | 'deliberate' | 'variable' {
    const avgHesitation = this.hesitations.length > 0 ?
      this.hesitations.reduce((sum, h) => sum + h.duration, 0) / this.hesitations.length : 500;
    
    if (avgHesitation < 300) return 'fast';
    if (avgHesitation > 1000) return 'deliberate';
    return 'variable';
  }
  
  private calculateErrorRecoveryScore(): number {
    // Score based on how well errors are recovered from
    const totalCorrections = this.corrections.length;
    const successfulCorrections = this.corrections.filter(c => c.successRate > 0.8).length;
    
    return totalCorrections > 0 ? successfulCorrections / totalCorrections : 0.8;
  }
  
  private calculateExplorationTendency(): number {
    // Tendency to explore interface vs. direct action
    // This would need more sophisticated tracking
    return 0.6; // Placeholder
  }
  
  private calculateCautionLevel(): number {
    // Level of caution in actions
    const avgHesitation = this.hesitations.length > 0 ?
      this.hesitations.reduce((sum, h) => sum + h.duration, 0) / this.hesitations.length : 500;
    
    return Math.min(1, avgHesitation / 1000); // Normalize to 0-1
  }
}

// Export the advanced biometric analytics class
export default AdvancedBiometricAnalytics;

// Also provide global access
declare global {
  interface Window {
    AdvancedBiometricAnalytics: typeof AdvancedBiometricAnalytics;
  }
}

if (typeof window !== 'undefined') {
  window.AdvancedBiometricAnalytics = AdvancedBiometricAnalytics;
}