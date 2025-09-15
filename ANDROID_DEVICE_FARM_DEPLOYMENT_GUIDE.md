# 🚀 Android Device Farm Deployment Guide for Snapchat Account Creation

## 📋 Overview
This guide shows you how to deploy Android emulators to Fly.io and connect your local Snapchat automation to remote Android devices.

## ✅ What We've Created
1. **Android Emulator Docker Configuration** (`Dockerfile.android`)
2. **Fly.io Configuration** (`fly-android.toml`) 
3. **Deployment Script** (`deploy_android_farm.sh`)
4. **Remote Connection Manager** (`android_remote_config.py`)

## 🔧 Manual Deployment Steps

### Step 1: Authenticate with Fly.io
```bash
# If flyctl is not installed, run this first:
curl -L https://fly.io/install.sh | sh
export PATH="$HOME/.fly/bin:$PATH"

# Authenticate (use your token)
flyctl auth login
```

### Step 2: Deploy Android Device Farm
```bash
# Make deployment script executable
chmod +x deploy_android_farm.sh

# Deploy the Android device farm
./deploy_android_farm.sh
```

**OR manually deploy with:**
```bash
# Create app
flyctl apps create android-device-farm-prod

# Create volume for Android data
flyctl volumes create android_data --region ord --size 20 --app android-device-farm-prod

# Set environment secrets
flyctl secrets set \
    REDIS_URL="redis://localhost:6379" \
    TWILIO_ACCOUNT_SID="ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" \
    TWILIO_AUTH_TOKEN="<twilio_auth_token>" \
    --app android-device-farm-prod

# Deploy using Android configuration
flyctl deploy --app android-device-farm-prod --config fly-android.toml --dockerfile Dockerfile.android

# Scale to high-memory instance
flyctl scale vm shared-cpu-4x --app android-device-farm-prod
flyctl scale count 1 --app android-device-farm-prod

# Allocate IP address
flyctl ips allocate-v4 --app android-device-farm-prod
```

### Step 3: Get Connection Details
```bash
# Get app status
flyctl status --app android-device-farm-prod

# Get IP address
flyctl ips list --app android-device-farm-prod

# Check logs
flyctl logs --app android-device-farm-prod -f
```

### Step 4: Connect Local Snapchat Automation to Remote Devices

#### Option A: Use the Remote Android Manager
```python
from android_remote_config import connect_to_fly_android_devices

# Connect to Fly.io Android devices
device_ids = connect_to_fly_android_devices()
print(f"Connected devices: {device_ids}")
```

#### Option B: Manual ADB Connection
```bash
# Get your Fly.io app IP address
FLY_IP=$(flyctl ips list --app android-device-farm-prod | grep "v4" | awk '{print $3}')

# Connect ADB to remote device
adb connect $FLY_IP:5555

# Verify connection
adb devices
```

### Step 5: Test Snapchat Account Creation
```python
import os
from automation.snapchat.stealth_creator import SnapchatStealthCreator
from android_remote_config import get_remote_android_manager

# Set environment variables
os.environ['REDIS_URL'] = 'redis://localhost:6379/0'
os.environ['TWILIO_ACCOUNT_SID'] = 'YOUR_TWILIO_ACCOUNT_SID'
os.environ['TWILIO_AUTH_TOKEN'] = '1234567890abcdef1234567890abcdef'

# Connect to remote Android device
manager = get_remote_android_manager()
device = manager.connect_to_fly_android_farm()

if device:
    # Create Snapchat account using remote device
    creator = SnapchatStealthCreator()
    profile = creator.generate_stealth_profile()
    
    result = creator.create_account(profile, device.device_id)
    print(f"Account creation result: {result.success}")
```

## 📱 Device Farm Features

### Available Ports:
- **5000**: Main application (HTTP API)
- **5555**: ADB connection
- **5900**: VNC (remote desktop access)

### Device Specifications:
- **OS**: Android 11.0 (API 30)
- **RAM**: 8GB allocated to VM
- **Storage**: 20GB persistent volume
- **Display**: Virtual display (1080x2340)
- **Features**: Camera, GPS, sensors enabled

### Remote Access:
```bash
# ADB connection
adb connect <FLY_IP>:5555

# VNC connection (view emulator screen)
# Use any VNC client: vnc://<FLY_IP>:5900

# SSH into container
flyctl ssh console --app android-device-farm-prod
```

## 🔍 Monitoring & Debugging

### Check Device Status:
```bash
# View logs
flyctl logs --app android-device-farm-prod -f

# SSH into container
flyctl ssh console --app android-device-farm-prod

# Inside container, check emulator
adb devices
adb shell getprop sys.boot_completed
```

### Health Checks:
```bash
# Check app health
curl https://android-device-farm-prod.fly.dev/health

# Check device status via API
curl https://android-device-farm-prod.fly.dev/api/devices
```

### Troubleshooting:
1. **Device not connecting**: Check firewall, verify IP/port
2. **Emulator not starting**: Check logs, may need VM restart
3. **ADB timeouts**: Increase ADB timeout, check network latency
4. **Performance issues**: Scale to higher VM size

## 🧪 Test Commands

### Test Device Connection:
```python
# Test the remote connection
python3 android_remote_config.py
```

### Test Snapchat Workflow:
```bash
# Test with current environment
python3 -c "
from automation.snapchat.stealth_creator import SnapchatStealthCreator
from android_remote_config import connect_to_fly_android_devices

devices = connect_to_fly_android_devices()
if devices:
    creator = SnapchatStealthCreator()
    profile = creator.generate_stealth_profile()
    result = creator.create_account(profile, devices[0])
    print(f'Success: {result.success}, Error: {result.error}')
"
```

## 🎯 Expected Results

After successful deployment:
1. ✅ **Android emulator running** on Fly.io
2. ✅ **ADB connection** working remotely  
3. ✅ **Snapchat automation** connecting to remote device
4. ✅ **Account creation** working end-to-end

### Success Indicators:
```bash
# These commands should work:
adb devices                          # Shows "device" status
adb shell getprop sys.boot_completed # Returns "1"
adb shell dumpsys window windows     # Shows UI is active
```

## 📞 Support

If deployment fails:
1. Check Fly.io app status: `flyctl status --app android-device-farm-prod`
2. Review logs: `flyctl logs --app android-device-farm-prod`
3. Verify authentication: `flyctl auth whoami`
4. Test local ADB: `adb version`

## 🚀 Next Steps

Once Android devices are running on Fly.io:
1. **Test account creation** with various profiles
2. **Monitor performance** and costs
3. **Scale up** if needed (multiple devices)
4. **Integrate with production** workflow

---

**Status**: ✅ All configuration files created and ready for deployment
**Ready to Deploy**: Run `./deploy_android_farm.sh` after Fly.io authentication