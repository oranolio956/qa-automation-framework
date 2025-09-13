# Tinder Account Automation System

A comprehensive, production-ready system for automating Tinder account creation and management with advanced anti-detection measures.

## 🚀 Features

### Core Automation
- **Full Account Creation Pipeline**: Automated Tinder registration with phone verification
- **Snapchat Integration**: Creates stealth Snapchat accounts and embeds usernames in Tinder bios
- **Advanced Anti-Detection**: Residential proxies, realistic touch patterns, human-like behavior
- **Account Warming**: Sophisticated scheduling system to avoid bans
- **Profile Management**: Automated bio updates, photo optimization, and profile enhancement

### Anti-Detection Measures
- **Residential Proxy Integration**: Uses Bright Data residential proxies for all requests
- **Device Fingerprinting**: Consistent device identities across sessions  
- **Bezier Curve Touch Simulation**: Natural gesture patterns with micro-jitter
- **Behavioral Modeling**: Human-like timing, session lengths, and activity patterns
- **CAPTCHA Detection**: Automatic puzzle/challenge detection and handling
- **Reinforcement Learning**: Adaptive behavior patterns based on success rates

### Scaling & Infrastructure
- **Android Emulator Pool**: Manages multiple Android devices simultaneously
- **Parallel Processing**: Creates accounts in parallel across multiple emulators
- **Redis State Management**: Persistent session state and activity logging
- **Warming Scheduler**: Background process for gradual account activity ramp-up
- **Error Recovery**: Adaptive retry logic and graceful failure handling

## 📋 Prerequisites

### System Requirements
- **Python 3.8+** with pip
- **Android SDK** with emulator support
- **Redis Server** for state management
- **Bright Data Account** for residential proxies
- **Twilio Account** for SMS verification

### Android SDK Setup
```bash
# Download Android SDK
wget https://dl.google.com/android/repository/commandlinetools-linux-8512546_latest.zip
unzip commandlinetools-linux-8512546_latest.zip -d ~/Android/Sdk
export ANDROID_HOME=~/Android/Sdk
export PATH=$PATH:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/emulator

# Install system images
sdkmanager "system-images;android-30;google_apis;x86_64"
sdkmanager "system-images;android-31;google_apis_playstore;x86_64"
```

### Python Dependencies
```bash
cd automation/
pip install -r requirements.txt
```

### Environment Variables
```bash
# Bright Data Proxy
export BRIGHTDATA_PROXY_URL="http://user:pass@brd.superproxy.io:9222"

# Twilio SMS (multiple accounts for pool)
export TWILIO_ACCOUNT_SID="your_account_sid"
export TWILIO_AUTH_TOKEN="your_auth_token"

# Redis
export REDIS_URL="redis://localhost:6379"
```

## 🛠 Installation

1. **Clone and Setup**
```bash
git clone <repository>
cd Tinder/automation
pip install -r requirements.txt
```

2. **Configure Services**
```bash
# Start Redis
redis-server

# Verify proxy connection
python -c "from utils.brightdata_proxy import verify_proxy; verify_proxy()"

# Test SMS verification
python -c "from utils.sms_verifier import get_sms_verifier; print(get_sms_verifier().get_statistics())"
```

3. **Download APKs** (Required)
```bash
# Place Tinder and Snapchat APKs in automation/apks/
mkdir -p apks/
# Download tinder.apk and snapchat.apk to this directory
```

## 🎯 Usage

### Quick Start
```bash
# Create 3 Tinder accounts with Snapchat integration
python main_orchestrator.py \
  --tinder-accounts 3 \
  --snapchat-accounts 3 \
  --emulators 3 \
  --aggressiveness 0.3 \
  --output ./results
```

### Advanced Usage
```bash
# High-volume parallel creation
python main_orchestrator.py \
  --tinder-accounts 20 \
  --snapchat-accounts 20 \
  --emulators 10 \
  --aggressiveness 0.5 \
  --parallel \
  --output ./batch_results

# Conservative warming mode
python main_orchestrator.py \
  --tinder-accounts 5 \
  --aggressiveness 0.1 \
  --no-warming \
  --output ./conservative
```

### Individual Components

#### Create Emulator Pool
```python
from android.emulator_manager import get_emulator_manager

manager = get_emulator_manager()
emulators = manager.create_emulator_pool(count=5, headless=True)
```

#### Create Snapchat Accounts
```python
from snapchat.stealth_creator import get_snapchat_creator

creator = get_snapchat_creator()
results = creator.create_multiple_accounts(count=3, device_ids=['emulator-5554'])
usernames = [r.profile.username for r in results if r.success]
```

#### Create Tinder Accounts
```python
from tinder.account_creator import get_account_creator

creator = get_account_creator(aggressiveness=0.3)
profile = creator.generate_random_profile(snapchat_username='john_doe123')
result = creator.create_account(profile, emulator_instance)
```

#### Start Account Warming
```python
from tinder.warming_scheduler import get_warming_manager

warming = get_warming_manager()
warming.add_account_for_warming(account_result, device_id)
warming.start_warming_scheduler()
```

## 🔧 Configuration

### Aggressiveness Levels
- **0.1-0.2**: Ultra-conservative (2-8 min sessions, 3-8 hour breaks)
- **0.3-0.4**: Conservative (5-15 min sessions, 2-6 hour breaks)  
- **0.5-0.7**: Moderate (8-25 min sessions, 1.5-5 hour breaks)
- **0.8-1.0**: Aggressive (10-35 min sessions, 1-4 hour breaks)

### Warming Schedule Phases
1. **Day 1**: Ultra-conservative (15 activities, 15% right swipes)
2. **Week 1**: Conservative (35 activities, 25% right swipes)  
3. **Week 2**: Moderate (60 activities, 35% right swipes)
4. **Active**: Full activity (100 activities, 45% right swipes)

### Anti-Detection Features
```python
# Device fingerprinting
fingerprint = anti_detection.create_device_fingerprint(device_id)

# Behavior patterns  
delay = behavior_pattern.get_swipe_timing()  # 0.8-12s with log-normal distribution
session_time = behavior_pattern.get_session_duration()  # 2-35 minutes

# Touch simulation
points = touch_generator.generate_bezier_swipe(start, end)  # Natural curve with jitter
```

## 📊 Monitoring & Analytics

### Real-time Statistics
```python
# Account creation stats
stats = account_creator.get_creation_statistics()
print(f"Success rate: {stats['success_rate']:.1%}")

# Warming system status
warming_stats = warming_manager.get_warming_statistics()
print(f"Active accounts: {warming_stats['status_breakdown']['active']}")

# Anti-detection verification
stealth_results = anti_detection.verify_stealth_setup()
print(f"Stealth systems: {stealth_results}")
```

### Output Files
- `automation_report.json`: Complete execution summary
- `tinder_results.json`: Detailed Tinder account creation results
- `snapchat_results.json`: Snapchat account creation results
- `warming_logs/`: Daily warming activity logs

## 🛡 Security & Stealth

### Proxy Configuration
- **Residential IPs Only**: Uses Bright Data residential proxy network
- **Session Consistency**: Same IP maintained throughout account lifecycle  
- **Rotation Strategy**: Automatic IP rotation between accounts
- **Geographic Targeting**: US-based IPs for realistic location data

### CAPTCHA Handling
- **Detection**: OCR-based CAPTCHA/puzzle detection
- **Solving**: Integration points for solving services
- **Fallback**: Manual intervention alerts for complex challenges

### Phone Verification
- **Twilio Pool**: Dynamic phone number pool management
- **SMS Parsing**: Automatic verification code extraction
- **Retry Logic**: Multiple verification attempts with backoff

## 🔄 Account Warming Details

### Warming Activities
- App opens and closes
- Profile viewing (scrolling, photo viewing)
- Natural swiping patterns (left/right ratios)
- Message reading and sending
- Settings and profile edits
- Super likes (limited frequency)

### Timing Safeguards
- **Session Limits**: Strict duration controls
- **Break Enforcement**: Mandatory cooldown periods
- **Daily Limits**: Maximum activities per day
- **Error Monitoring**: Automatic suspension on failures

## 🚨 Error Handling

### Automatic Recovery
- **Network Issues**: Retry with exponential backoff
- **App Crashes**: Automatic restart and state recovery
- **Verification Failures**: Alternative phone number attempts
- **CAPTCHA Blocks**: Pause and manual intervention alerts

### Monitoring Alerts
- **Account Suspensions**: Immediate notifications
- **High Error Rates**: Automatic aggressiveness reduction
- **Proxy Issues**: Failover to backup connections
- **Resource Exhaustion**: Scale-down recommendations

## 📈 Performance Optimization

### Parallelization
- **Account Creation**: Up to 10 parallel streams
- **Warming Activities**: Background scheduling
- **Photo Processing**: Async optimization pipeline
- **SMS Verification**: Concurrent verification handling

### Resource Management  
- **Memory Efficiency**: Emulator pool management
- **CPU Usage**: Throttled activity execution
- **Network Bandwidth**: Request batching and caching
- **Storage**: Automatic log rotation and cleanup

## 🎛 Advanced Configuration

### Custom Warming Schedules
```python
custom_schedule = WarmingSchedule(
    status=AccountStatus.CUSTOM,
    daily_sessions=4,
    session_duration_min=10,
    session_duration_max=20,
    activities_per_session=50,
    swipe_ratio_right=0.3,
    super_like_frequency=0.5
)
```

### Profile Customization
```python
# Custom bio generation
bio_generator = BioGenerator()
bio = bio_generator.generate_bio(
    snapchat_username="user123",
    interests=['travel', 'fitness', 'dogs']
)

# Photo optimization
photo_processor = PhotoProcessor()
optimized_path = photo_processor.optimize_photo("photo.jpg")
```

## 🔍 Troubleshooting

### Common Issues
1. **Emulator Start Failures**: Check Android SDK installation and AVD creation
2. **Proxy Connection Issues**: Verify Bright Data credentials and network
3. **SMS Verification Problems**: Check Twilio account balance and number pool
4. **App Installation Failures**: Ensure APK files are present and device compatible

### Debug Mode
```bash
# Enable verbose logging
export LOG_LEVEL=DEBUG
python main_orchestrator.py --tinder-accounts 1 --aggressiveness 0.1
```

### Performance Tuning
```bash
# Optimize for speed
python main_orchestrator.py --parallel --aggressiveness 0.8 --no-warming

# Optimize for stealth  
python main_orchestrator.py --aggressiveness 0.1 --emulators 2
```

## 📄 License

This automation system is for educational and testing purposes only. Users are responsible for complying with all applicable terms of service and local laws.

## 🤝 Support

For technical support and feature requests, please refer to the project documentation or contact the development team.