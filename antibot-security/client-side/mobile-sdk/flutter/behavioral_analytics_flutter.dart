/**
 * Flutter Mobile SDK for Behavioral Analytics
 * Cross-platform device fingerprinting and emulator detection
 * Supports both Android and iOS with native performance
 */

import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';
import 'dart:typed_data';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:device_info_plus/device_info_plus.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:crypto/crypto.dart';
import 'package:sensors_plus/sensors_plus.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:package_info_plus/package_info_plus.dart';

// Data Models
class TouchGestureData {
  final int identifier;
  final double localX;
  final double localY;
  final double globalX;
  final double globalY;
  final DateTime timestamp;
  final double? pressure;
  final double? size;
  final double? velocity;
  final double? acceleration;

  TouchGestureData({
    required this.identifier,
    required this.localX,
    required this.localY,
    required this.globalX,
    required this.globalY,
    required this.timestamp,
    this.pressure,
    this.size,
    this.velocity,
    this.acceleration,
  });

  Map<String, dynamic> toJson() => {
    'identifier': identifier,
    'localX': localX,
    'localY': localY,
    'globalX': globalX,
    'globalY': globalY,
    'timestamp': timestamp.millisecondsSinceEpoch,
    'pressure': pressure,
    'size': size,
    'velocity': velocity,
    'acceleration': acceleration,
  };
}

class BehavioralEventFlutter {
  final String type;
  final String? subtype;
  final DateTime timestamp;
  final String sessionId;
  final Map<String, dynamic> data;
  final String? deviceFingerprint;

  BehavioralEventFlutter({
    required this.type,
    this.subtype,
    required this.timestamp,
    required this.sessionId,
    required this.data,
    this.deviceFingerprint,
  });

  Map<String, dynamic> toJson() => {
    'type': type,
    'subtype': subtype,
    'timestamp': timestamp.millisecondsSinceEpoch,
    'sessionId': sessionId,
    'data': data,
    'deviceFingerprint': deviceFingerprint,
  };
}

class DeviceFingerprintFlutter {
  final String deviceId;
  final String platform;
  final String version;
  final String model;
  final String brand;
  final String? buildNumber;
  final String? appVersion;
  final String deviceName;
  final String systemVersion;
  final Map<String, dynamic> screenDimensions;
  final Map<String, dynamic> networkInfo;
  final Map<String, dynamic> sensors;
  final Map<String, dynamic> security;
  final String hash;

  DeviceFingerprintFlutter({
    required this.deviceId,
    required this.platform,
    required this.version,
    required this.model,
    required this.brand,
    this.buildNumber,
    this.appVersion,
    required this.deviceName,
    required this.systemVersion,
    required this.screenDimensions,
    required this.networkInfo,
    required this.sensors,
    required this.security,
    required this.hash,
  });

  Map<String, dynamic> toJson() => {
    'deviceId': deviceId,
    'platform': platform,
    'version': version,
    'model': model,
    'brand': brand,
    'buildNumber': buildNumber,
    'appVersion': appVersion,
    'deviceName': deviceName,
    'systemVersion': systemVersion,
    'screenDimensions': screenDimensions,
    'networkInfo': networkInfo,
    'sensors': sensors,
    'security': security,
    'hash': hash,
  };
}

class EmulatorDetectionResult {
  final bool isEmulator;
  final double confidence;
  final List<String> indicators;
  final String riskLevel;

  EmulatorDetectionResult({
    required this.isEmulator,
    required this.confidence,
    required this.indicators,
    required this.riskLevel,
  });

  Map<String, dynamic> toJson() => {
    'isEmulator': isEmulator,
    'confidence': confidence,
    'indicators': indicators,
    'riskLevel': riskLevel,
  };
}

class BehavioralAnalyticsConfig {
  final String apiEndpoint;
  final int sessionTimeout;
  final int batchSize;
  final int flushInterval;
  final bool enableTouchTracking;
  final bool enableGestureAnalysis;
  final bool enableEmulatorDetection;
  final bool enableSensorData;
  final bool privacyMode;
  final bool consentRequired;
  final int performanceThreshold;
  final bool offlineStorageEnabled;

  BehavioralAnalyticsConfig({
    this.apiEndpoint = 'https://api.example.com/v1/behavioral-data',
    this.sessionTimeout = 1800000, // 30 minutes
    this.batchSize = 30,
    this.flushInterval = 10000, // 10 seconds
    this.enableTouchTracking = true,
    this.enableGestureAnalysis = true,
    this.enableEmulatorDetection = true,
    this.enableSensorData = true,
    this.privacyMode = false,
    this.consentRequired = false,
    this.performanceThreshold = 50,
    this.offlineStorageEnabled = true,
  });
}

// Main Behavioral Analytics Class
class BehavioralAnalyticsFlutter {
  final BehavioralAnalyticsConfig config;
  late String sessionId;
  final List<BehavioralEventFlutter> _events = [];
  DeviceFingerprintFlutter? _deviceFingerprint;
  EmulatorDetectionResult? _emulatorDetection;
  final List<TouchGestureData> _touchBuffer = [];
  final List<Map<String, dynamic>> _gesturePatterns = [];
  final Map<String, dynamic> _sensorData = {};
  bool _isInitialized = false;
  bool _consentGiven = false;
  Timer? _transmissionTimer;
  Timer? _sensorTimer;
  final DateTime _startTime = DateTime.now();
  
  // Sensor subscriptions
  StreamSubscription<AccelerometerEvent>? _accelerometerSubscription;
  StreamSubscription<GyroscopeEvent>? _gyroscopeSubscription;
  StreamSubscription<MagnetometerEvent>? _magnetometerSubscription;

  BehavioralAnalyticsFlutter(this.config) {
    sessionId = _generateSessionId();
    _initialize();
  }

  // Initialize the analytics system
  Future<void> _initialize() async {
    try {
      final startTime = DateTime.now();

      // Handle consent if required
      if (config.consentRequired) {
        await _handleConsentRequirement();
      } else {
        _consentGiven = true;
      }

      if (!_consentGiven) return;

      // Generate device fingerprint
      _deviceFingerprint = await _generateDeviceFingerprint();

      // Perform emulator detection
      if (config.enableEmulatorDetection) {
        _emulatorDetection = await _detectEmulator();
      }

      // Setup behavioral tracking
      _setupBehavioralTracking();

      // Start data transmission
      _startDataTransmission();

      final initTime = DateTime.now().difference(startTime).inMilliseconds;
      if (initTime > config.performanceThreshold) {
        debugPrint('Flutter analytics initialization took ${initTime}ms');
      }

      _isInitialized = true;
      debugPrint('Flutter Behavioral Analytics initialized successfully');

    } catch (error) {
      debugPrint('Failed to initialize Flutter Behavioral Analytics: $error');
    }
  }

  // Handle consent requirement
  Future<void> _handleConsentRequirement() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final existingConsent = prefs.getString('antibot_flutter_consent');
      
      if (existingConsent == 'granted') {
        _consentGiven = true;
        return;
      }

      // In a real implementation, you would show a consent dialog here
      // For this example, we'll assume consent is granted
      _consentGiven = true;
      await prefs.setString('antibot_flutter_consent', 'granted');

    } catch (error) {
      debugPrint('Error handling consent: $error');
      _consentGiven = false;
    }
  }

  // Generate unique session ID
  String _generateSessionId() {
    final timestamp = DateTime.now().millisecondsSinceEpoch.toRadixString(36);
    final random = Random().nextInt(1000000).toRadixString(36);
    final platform = Platform.isAndroid ? 'android' : 'ios';
    return '$platform-$timestamp-$random';
  }

  // Generate comprehensive device fingerprint
  Future<DeviceFingerprintFlutter> _generateDeviceFingerprint() async {
    final startTime = DateTime.now();
    
    try {
      final deviceInfo = DeviceInfoPlugin();
      final packageInfo = await PackageInfo.fromPlatform();
      final connectivity = Connectivity();
      
      String deviceId = '';
      String model = '';
      String brand = '';
      String deviceName = '';
      String systemVersion = '';
      Map<String, dynamic> additionalInfo = {};

      if (Platform.isAndroid) {
        final androidInfo = await deviceInfo.androidInfo;
        deviceId = androidInfo.id;
        model = androidInfo.model;
        brand = androidInfo.brand;
        deviceName = androidInfo.device;
        systemVersion = androidInfo.version.release;
        additionalInfo = {
          'manufacturer': androidInfo.manufacturer,
          'product': androidInfo.product,
          'hardware': androidInfo.hardware,
          'bootloader': androidInfo.bootloader,
          'board': androidInfo.board,
          'host': androidInfo.host,
          'fingerprint': androidInfo.fingerprint,
          'buildId': androidInfo.id,
          'sdkInt': androidInfo.version.sdkInt,
          'isPhysicalDevice': androidInfo.isPhysicalDevice,
          'systemFeatures': androidInfo.systemFeatures,
        };
      } else if (Platform.isIOS) {
        final iosInfo = await deviceInfo.iosInfo;
        deviceId = iosInfo.identifierForVendor ?? '';
        model = iosInfo.model;
        brand = 'Apple';
        deviceName = iosInfo.name;
        systemVersion = iosInfo.systemVersion;
        additionalInfo = {
          'localizedModel': iosInfo.localizedModel,
          'systemName': iosInfo.systemName,
          'utsname': iosInfo.utsname.toMap(),
          'isPhysicalDevice': iosInfo.isPhysicalDevice,
        };
      }

      // Screen dimensions
      final screenDimensions = {
        'width': WidgetsBinding.instance.window.physicalSize.width,
        'height': WidgetsBinding.instance.window.physicalSize.height,
        'devicePixelRatio': WidgetsBinding.instance.window.devicePixelRatio,
        'padding': {
          'top': WidgetsBinding.instance.window.padding.top,
          'bottom': WidgetsBinding.instance.window.padding.bottom,
          'left': WidgetsBinding.instance.window.padding.left,
          'right': WidgetsBinding.instance.window.padding.right,
        },
      };

      // Network info
      final connectivityResult = await connectivity.checkConnectivity();
      final networkInfo = {
        'type': connectivityResult.toString(),
        'timestamp': DateTime.now().millisecondsSinceEpoch,
      };

      // Sensor availability
      final sensors = await _detectAvailableSensors();

      // Security checks
      final security = await _performSecurityChecks(additionalInfo);

      final fingerprint = DeviceFingerprintFlutter(
        deviceId: config.privacyMode ? _hashString(deviceId) : deviceId,
        platform: Platform.operatingSystem,
        version: Platform.operatingSystemVersion,
        model: model,
        brand: brand,
        buildNumber: additionalInfo['buildId']?.toString(),
        appVersion: packageInfo.version,
        deviceName: config.privacyMode ? 'masked' : deviceName,
        systemVersion: systemVersion,
        screenDimensions: screenDimensions,
        networkInfo: networkInfo,
        sensors: sensors,
        security: security,
        hash: '',
      );

      // Generate hash
      final hash = _hashString(jsonEncode(fingerprint.toJson()));
      final hashedFingerprint = DeviceFingerprintFlutter(
        deviceId: fingerprint.deviceId,
        platform: fingerprint.platform,
        version: fingerprint.version,
        model: fingerprint.model,
        brand: fingerprint.brand,
        buildNumber: fingerprint.buildNumber,
        appVersion: fingerprint.appVersion,
        deviceName: fingerprint.deviceName,
        systemVersion: fingerprint.systemVersion,
        screenDimensions: fingerprint.screenDimensions,
        networkInfo: fingerprint.networkInfo,
        sensors: fingerprint.sensors,
        security: fingerprint.security,
        hash: hash,
      );

      final processingTime = DateTime.now().difference(startTime).inMilliseconds;
      debugPrint('Device fingerprint generated in ${processingTime}ms');

      return hashedFingerprint;

    } catch (error) {
      debugPrint('Error generating device fingerprint: $error');
      rethrow;
    }
  }

  // Detect available sensors
  Future<Map<String, dynamic>> _detectAvailableSensors() async {
    final sensors = <String, bool>{};
    
    try {
      // Test accelerometer
      final accelCompleter = Completer<bool>();
      final accelSub = accelerometerEvents.listen(
        (_) => accelCompleter.complete(true),
        onError: (_) => accelCompleter.complete(false),
      );
      
      Timer(const Duration(milliseconds: 100), () {
        if (!accelCompleter.isCompleted) accelCompleter.complete(false);
      });
      
      sensors['accelerometer'] = await accelCompleter.future;
      accelSub.cancel();

      // Test gyroscope
      final gyroCompleter = Completer<bool>();
      final gyroSub = gyroscopeEvents.listen(
        (_) => gyroCompleter.complete(true),
        onError: (_) => gyroCompleter.complete(false),
      );
      
      Timer(const Duration(milliseconds: 100), () {
        if (!gyroCompleter.isCompleted) gyroCompleter.complete(false);
      });
      
      sensors['gyroscope'] = await gyroCompleter.future;
      gyroSub.cancel();

      // Test magnetometer
      final magCompleter = Completer<bool>();
      final magSub = magnetometerEvents.listen(
        (_) => magCompleter.complete(true),
        onError: (_) => magCompleter.complete(false),
      );
      
      Timer(const Duration(milliseconds: 100), () {
        if (!magCompleter.isCompleted) magCompleter.complete(false);
      });
      
      sensors['magnetometer'] = await magCompleter.future;
      magSub.cancel();

    } catch (error) {
      debugPrint('Error detecting sensors: $error');
    }

    return {
      'available': sensors,
      'count': sensors.values.where((available) => available).length,
    };
  }

  // Perform security checks
  Future<Map<String, dynamic>> _performSecurityChecks(Map<String, dynamic> deviceInfo) async {
    final security = <String, dynamic>{};

    try {
      // Check if running on emulator
      bool isEmulator = false;
      
      if (Platform.isAndroid) {
        final androidInfo = deviceInfo;
        isEmulator = !androidInfo['isPhysicalDevice'] as bool? ?? false;
        
        // Additional Android emulator checks
        final fingerprint = androidInfo['fingerprint']?.toString().toLowerCase() ?? '';
        final model = androidInfo['model']?.toString().toLowerCase() ?? '';
        final manufacturer = androidInfo['manufacturer']?.toString().toLowerCase() ?? '';
        final brand = androidInfo['brand']?.toString().toLowerCase() ?? '';
        final product = androidInfo['product']?.toString().toLowerCase() ?? '';
        
        isEmulator = isEmulator ||
          fingerprint.contains('generic') ||
          fingerprint.contains('unknown') ||
          model.contains('google_sdk') ||
          model.contains('emulator') ||
          model.contains('android sdk built for x86') ||
          manufacturer.contains('genymotion') ||
          brand.contains('generic') ||
          product.contains('sdk') ||
          product.contains('emulator');
        
      } else if (Platform.isIOS) {
        final iosInfo = deviceInfo;
        isEmulator = !iosInfo['isPhysicalDevice'] as bool? ?? false;
        
        // Additional iOS simulator checks
        final model = iosInfo['model']?.toString().toLowerCase() ?? '';
        isEmulator = isEmulator || model.contains('simulator');
      }

      security['isEmulator'] = isEmulator;
      security['isRooted'] = await _detectRootedDevice();
      security['isDebuggingEnabled'] = kDebugMode;
      security['hasMockLocation'] = false; // Placeholder

    } catch (error) {
      debugPrint('Error performing security checks: $error');
      security['isEmulator'] = false;
      security['isRooted'] = false;
      security['isDebuggingEnabled'] = false;
      security['hasMockLocation'] = false;
    }

    return security;
  }

  // Detect rooted/jailbroken device
  Future<bool> _detectRootedDevice() async {
    try {
      if (Platform.isAndroid) {
        // Check for common root indicators on Android
        const rootPaths = [
          '/system/app/Superuser.apk',
          '/sbin/su',
          '/system/bin/su',
          '/system/xbin/su',
          '/data/local/xbin/su',
          '/data/local/bin/su',
          '/system/sd/xbin/su',
          '/system/bin/failsafe/su',
          '/data/local/su',
        ];

        for (final path in rootPaths) {
          if (await File(path).exists()) {
            return true;
          }
        }

        // Check for root management apps
        const rootApps = [
          'com.noshufou.android.su',
          'com.thirdparty.superuser',
          'eu.chainfire.supersu',
          'com.koushikdutta.superuser',
          'com.zachspong.temprootremovejb',
          'com.ramdroid.appquarantine',
        ];

        // This would require additional platform-specific implementation
        // to check installed packages

      } else if (Platform.isIOS) {
        // Check for common jailbreak indicators on iOS
        const jailbreakPaths = [
          '/Applications/Cydia.app',
          '/Library/MobileSubstrate/MobileSubstrate.dylib',
          '/bin/bash',
          '/usr/sbin/sshd',
          '/etc/apt',
          '/usr/bin/ssh',
        ];

        for (final path in jailbreakPaths) {
          if (await File(path).exists()) {
            return true;
          }
        }
      }

      return false;
    } catch (error) {
      debugPrint('Error detecting root: $error');
      return false;
    }
  }

  // Comprehensive emulator detection
  Future<EmulatorDetectionResult> _detectEmulator() async {
    final indicators = <String>[];
    double confidence = 0;

    try {
      // Basic device info checks
      if (_deviceFingerprint?.security['isEmulator'] == true) {
        indicators.add('Device info indicates emulator');
        confidence += 0.8;
      }

      // Hardware-based detection
      final model = _deviceFingerprint?.model.toLowerCase() ?? '';
      final brand = _deviceFingerprint?.brand.toLowerCase() ?? '';
      
      if (Platform.isAndroid) {
        final emulatorModels = [
          'android sdk built for x86',
          'emulator',
          'sdk_gphone',
          'google_sdk'
        ];
        
        final emulatorBrands = ['generic', 'android', 'google'];
        
        if (emulatorModels.any((em) => model.contains(em))) {
          indicators.add('Emulator model detected: $model');
          confidence += 0.6;
        }
        
        if (emulatorBrands.any((eb) => brand.contains(eb))) {
          indicators.add('Emulator brand detected: $brand');
          confidence += 0.4;
        }
      }

      // Screen resolution checks
      final screenWidth = _deviceFingerprint?.screenDimensions['width'] ?? 0;
      final screenHeight = _deviceFingerprint?.screenDimensions['height'] ?? 0;
      
      // Common emulator resolutions
      final commonEmulatorResolutions = [
        [1080, 1920],
        [720, 1280],
        [480, 800],
        [320, 480],
      ];
      
      for (final resolution in commonEmulatorResolutions) {
        if ((screenWidth == resolution[0] && screenHeight == resolution[1]) ||
            (screenWidth == resolution[1] && screenHeight == resolution[0])) {
          indicators.add('Common emulator screen resolution detected');
          confidence += 0.2;
          break;
        }
      }

      // Sensor availability checks
      final sensorCount = _deviceFingerprint?.sensors['count'] ?? 0;
      if (sensorCount < 2) {
        indicators.add('Limited sensor availability');
        confidence += 0.3;
      }

      // Performance-based detection
      final devicePixelRatio = _deviceFingerprint?.screenDimensions['devicePixelRatio'] ?? 1.0;
      if (devicePixelRatio == 1.0) {
        indicators.add('Suspicious device pixel ratio');
        confidence += 0.1;
      }

      // Normalize confidence
      confidence = confidence.clamp(0.0, 1.0);

      String riskLevel;
      if (confidence >= 0.8) {
        riskLevel = 'high';
      } else if (confidence >= 0.5) {
        riskLevel = 'medium';
      } else {
        riskLevel = 'low';
      }

      return EmulatorDetectionResult(
        isEmulator: confidence > 0.5,
        confidence: confidence,
        indicators: indicators,
        riskLevel: riskLevel,
      );

    } catch (error) {
      debugPrint('Error in emulator detection: $error');
      return EmulatorDetectionResult(
        isEmulator: false,
        confidence: 0,
        indicators: ['Error during detection'],
        riskLevel: 'low',
      );
    }
  }

  // Setup behavioral tracking
  void _setupBehavioralTracking() {
    if (config.enableSensorData) {
      _setupSensorTracking();
    }
  }

  // Setup sensor tracking
  void _setupSensorTracking() {
    _sensorTimer = Timer.periodic(const Duration(seconds: 5), (_) {
      _collectSensorData();
    });

    // Subscribe to sensor streams
    if (config.enableSensorData) {
      _accelerometerSubscription = accelerometerEvents.listen(
        (AccelerometerEvent event) {
          _sensorData['accelerometer'] = {
            'x': event.x,
            'y': event.y,
            'z': event.z,
            'timestamp': DateTime.now().millisecondsSinceEpoch,
          };
        },
      );

      _gyroscopeSubscription = gyroscopeEvents.listen(
        (GyroscopeEvent event) {
          _sensorData['gyroscope'] = {
            'x': event.x,
            'y': event.y,
            'z': event.z,
            'timestamp': DateTime.now().millisecondsSinceEpoch,
          };
        },
      );

      _magnetometerSubscription = magnetometerEvents.listen(
        (MagnetometerEvent event) {
          _sensorData['magnetometer'] = {
            'x': event.x,
            'y': event.y,
            'z': event.z,
            'timestamp': DateTime.now().millisecondsSinceEpoch,
          };
        },
      );
    }
  }

  // Collect sensor data
  void _collectSensorData() {
    if (_sensorData.isNotEmpty) {
      _addEvent(BehavioralEventFlutter(
        type: 'sensor',
        timestamp: DateTime.now(),
        sessionId: sessionId,
        data: Map<String, dynamic>.from(_sensorData),
        deviceFingerprint: _deviceFingerprint?.hash,
      ));
    }
  }

  // Handle touch events (to be called from widget)
  void handleTouchEvent(String type, Offset localPosition, Offset globalPosition) {
    if (!config.enableTouchTracking || !_consentGiven) return;

    final timestamp = DateTime.now();
    final touchData = TouchGestureData(
      identifier: 0,
      localX: localPosition.dx,
      localY: localPosition.dy,
      globalX: globalPosition.dx,
      globalY: globalPosition.dy,
      timestamp: timestamp,
    );

    // Calculate velocity and acceleration
    if (_touchBuffer.isNotEmpty && type == 'move') {
      final lastTouch = _touchBuffer.last;
      final timeDiff = timestamp.difference(lastTouch.timestamp).inMilliseconds;
      if (timeDiff > 0) {
        final distance = (touchData.globalX - lastTouch.globalX).abs() +
                        (touchData.globalY - lastTouch.globalY).abs();
        touchData = TouchGestureData(
          identifier: touchData.identifier,
          localX: touchData.localX,
          localY: touchData.localY,
          globalX: touchData.globalX,
          globalY: touchData.globalY,
          timestamp: touchData.timestamp,
          pressure: touchData.pressure,
          size: touchData.size,
          velocity: distance / timeDiff,
        );

        if (_touchBuffer.length > 1) {
          final prevTouch = _touchBuffer[_touchBuffer.length - 2];
          final prevVelocity = prevTouch.velocity ?? 0;
          touchData = TouchGestureData(
            identifier: touchData.identifier,
            localX: touchData.localX,
            localY: touchData.localY,
            globalX: touchData.globalX,
            globalY: touchData.globalY,
            timestamp: touchData.timestamp,
            pressure: touchData.pressure,
            size: touchData.size,
            velocity: touchData.velocity,
            acceleration: (touchData.velocity! - prevVelocity) / timeDiff,
          );
        }
      }
    }

    _touchBuffer.add(touchData);
    if (_touchBuffer.length > 20) {
      _touchBuffer.removeAt(0);
    }

    _addEvent(BehavioralEventFlutter(
      type: 'touch',
      subtype: type,
      timestamp: timestamp,
      sessionId: sessionId,
      data: {
        'touch': touchData.toJson(),
        'gestureMetrics': _calculateGestureMetrics(),
      },
      deviceFingerprint: _deviceFingerprint?.hash,
    ));
  }

  // Calculate gesture metrics
  Map<String, dynamic> _calculateGestureMetrics() {
    if (_touchBuffer.length < 2) return {};

    final velocities = _touchBuffer
        .where((t) => t.velocity != null)
        .map((t) => t.velocity!)
        .toList();

    final accelerations = _touchBuffer
        .where((t) => t.acceleration != null)
        .map((t) => t.acceleration!)
        .toList();

    return {
      'avgVelocity': velocities.isNotEmpty 
          ? velocities.reduce((a, b) => a + b) / velocities.length 
          : 0,
      'maxVelocity': velocities.isNotEmpty ? velocities.reduce(max) : 0,
      'avgAcceleration': accelerations.isNotEmpty
          ? accelerations.reduce((a, b) => a + b) / accelerations.length
          : 0,
      'touchDuration': _touchBuffer.isNotEmpty
          ? _touchBuffer.last.timestamp.difference(_touchBuffer.first.timestamp).inMilliseconds
          : 0,
      'touchPoints': _touchBuffer.length,
    };
  }

  // Add event to buffer
  void _addEvent(BehavioralEventFlutter event) {
    if (!_consentGiven) return;

    _events.add(event);

    // Auto-flush if buffer is full
    if (_events.length >= config.batchSize) {
      _flushEvents();
    }
  }

  // Start data transmission
  void _startDataTransmission() {
    _transmissionTimer = Timer.periodic(
      Duration(milliseconds: config.flushInterval),
      (_) {
        if (_events.isNotEmpty) {
          _flushEvents();
        }
      },
    );
  }

  // Flush events to server
  Future<void> _flushEvents() async {
    if (_events.isEmpty) return;

    final eventsToSend = List<BehavioralEventFlutter>.from(_events);
    _events.clear();

    final payload = {
      'sessionId': sessionId,
      'deviceFingerprint': _deviceFingerprint?.toJson(),
      'emulatorDetection': _emulatorDetection?.toJson(),
      'events': eventsToSend.map((e) => e.toJson()).toList(),
      'metadata': {
        'platform': Platform.operatingSystem,
        'platformVersion': Platform.operatingSystemVersion,
        'sessionDuration': DateTime.now().difference(_startTime).inMilliseconds,
        'timestamp': DateTime.now().millisecondsSinceEpoch,
        'consentGiven': _consentGiven,
        'privacyMode': config.privacyMode,
      },
    };

    try {
      // This is a placeholder for actual HTTP request
      // In a real implementation, you would use http package
      debugPrint('Sending behavioral data: ${payload['events'].length} events');
      
      // Simulate API call
      await Future.delayed(const Duration(milliseconds: 100));
      
      // Handle response (placeholder)
      _handleServerResponse({'riskScore': 0.2});

    } catch (error) {
      debugPrint('Failed to send behavioral data: $error');
      
      // Store offline if enabled
      if (config.offlineStorageEnabled) {
        await _storeOffline(payload);
      }
    }
  }

  // Handle server response
  void _handleServerResponse(Map<String, dynamic> response) {
    final riskScore = response['riskScore'] as double?;
    
    if (riskScore != null) {
      debugPrint('Risk score: $riskScore');
      
      if (riskScore > 0.8) {
        _triggerSecurityAlert(response);
      }
    }
  }

  // Trigger security alert
  void _triggerSecurityAlert(Map<String, dynamic> response) {
    debugPrint('High risk detected - triggering security alert');
    // Implementation would depend on your app's UI framework
  }

  // Store data offline
  Future<void> _storeOffline(Map<String, dynamic> payload) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final existingData = prefs.getStringList('antibot_offline_data') ?? [];
      
      existingData.add(jsonEncode(payload));
      
      // Limit queue size
      if (existingData.length > 10) {
        existingData.removeAt(0);
      }
      
      await prefs.setStringList('antibot_offline_data', existingData);
    } catch (error) {
      debugPrint('Failed to store data offline: $error');
    }
  }

  // Hash string using SHA256
  String _hashString(String input) {
    final bytes = utf8.encode(input);
    final digest = sha256.convert(bytes);
    return digest.toString();
  }

  // Public API methods

  Map<String, dynamic> getSessionInfo() {
    return {
      'sessionId': sessionId,
      'isInitialized': _isInitialized,
      'consentGiven': _consentGiven,
      'deviceFingerprint': _deviceFingerprint?.toJson(),
      'emulatorDetection': _emulatorDetection?.toJson(),
      'eventCount': _events.length,
      'sessionDuration': DateTime.now().difference(_startTime).inMilliseconds,
    };
  }

  Future<void> grantConsent() async {
    _consentGiven = true;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('antibot_flutter_consent', 'granted');
    
    if (!_isInitialized) {
      await _initialize();
    }
  }

  Future<void> revokeConsent() async {
    _consentGiven = false;
    _events.clear();
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('antibot_flutter_consent');
    
    _transmissionTimer?.cancel();
    _sensorTimer?.cancel();
  }

  void flush() {
    _flushEvents();
  }

  void dispose() {
    _flushEvents();
    _transmissionTimer?.cancel();
    _sensorTimer?.cancel();
    _accelerometerSubscription?.cancel();
    _gyroscopeSubscription?.cancel();
    _magnetometerSubscription?.cancel();
    _events.clear();
    _touchBuffer.clear();
    _gesturePatterns.clear();
  }
}

// Widget for touch tracking
class BehavioralTrackingWidget extends StatefulWidget {
  final Widget child;
  final BehavioralAnalyticsFlutter analytics;

  const BehavioralTrackingWidget({
    Key? key,
    required this.child,
    required this.analytics,
  }) : super(key: key);

  @override
  State<BehavioralTrackingWidget> createState() => _BehavioralTrackingWidgetState();
}

class _BehavioralTrackingWidgetState extends State<BehavioralTrackingWidget> {
  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onPanStart: (details) => widget.analytics.handleTouchEvent(
        'start',
        details.localPosition,
        details.globalPosition,
      ),
      onPanUpdate: (details) => widget.analytics.handleTouchEvent(
        'move',
        details.localPosition,
        details.globalPosition,
      ),
      onPanEnd: (details) => widget.analytics.handleTouchEvent(
        'end',
        Offset.zero,
        Offset.zero,
      ),
      onTap: () => widget.analytics.handleTouchEvent(
        'tap',
        Offset.zero,
        Offset.zero,
      ),
      child: widget.child,
    );
  }
}

// Consent dialog widget
class ConsentDialog extends StatelessWidget {
  final VoidCallback onAccept;
  final VoidCallback onDecline;

  const ConsentDialog({
    Key? key,
    required this.onAccept,
    required this.onDecline,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Data Collection Consent'),
      content: const Text(
        'This app collects behavioral data for security purposes. '
        'This helps us detect and prevent fraudulent activity.',
      ),
      actions: [
        TextButton(
          onPressed: onDecline,
          child: const Text('Decline'),
        ),
        TextButton(
          onPressed: onAccept,
          child: const Text('Accept'),
        ),
      ],
    );
  }
}