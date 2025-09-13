# Android x86 Development Environment

A comprehensive setup for Android x86 virtualization and development tools, designed for app testing, development, and automation.

## Overview

This environment provides:
- KVM/QEMU virtualization with Android x86 VMs
- Complete Android SDK and development tools
- ADB connectivity and debugging capabilities
- Docker containers for isolated development
- Management scripts for common tasks

## Quick Start

### 1. Initial Setup

```bash
# Make scripts executable
chmod +x setup-android-dev.sh vm-management.sh development-tools.sh

# Run initial setup with Android ISO URL
./setup-android-dev.sh "https://osdn.net/projects/android-x86/downloads/71931/android-x86_64-9.0-r2.iso"

# Install development tools
./development-tools.sh
```

### 2. VM Management

```bash
# Start Android VM
./vm-management.sh start

# Check status
./vm-management.sh status

# Open VM console
./vm-management.sh console

# Connect ADB
./vm-management.sh adb-connect
```

### 3. Development Workflow

```bash
# Start development containers
docker-compose up -d

# Install APK to VM
./vm-management.sh install app.apk

# Take VM snapshot
./vm-management.sh snapshot my-snapshot

# Reset to clean state
./vm-management.sh reset
```

## System Requirements

- Ubuntu 20.04+ or Debian 11+
- 8GB+ RAM (16GB recommended)
- 50GB+ free disk space
- CPU with virtualization support (Intel VT-x or AMD-V)
- Internet connection for downloads

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Host System (Ubuntu)                     │
├─────────────────────────────────────────────────────────────┤
│ KVM/QEMU Virtualization                                    │
│ ├── Android x86 VM (8GB RAM, 4 vCPU, 32GB disk)          │
│ │   ├── Android 9.0/11.0 x86_64                          │
│ │   ├── Developer Options enabled                         │
│ │   └── ADB over TCP (port 5555)                         │
│ │                                                         │
│ Docker Containers                                          │
│ ├── Android SDK Tools                                     │
│ ├── Gradle Build Environment                              │
│ └── Development Dependencies                               │
│                                                            │
│ Development Tools                                          │
│ ├── Android SDK & Platform Tools                          │
│ ├── Node.js & React Native CLI                           │
│ ├── ADB & Fastboot                                       │
│ └── Testing & Debugging Tools                            │
└─────────────────────────────────────────────────────────────┘
```

### Network Configuration

- VM uses NAT networking via libvirt default network
- ADB connects to VM over TCP/IP
- VM accessible via SPICE console
- Port forwarding available for app testing

## File Structure

```
android-x86-dev/
├── setup-android-dev.sh      # Main setup script
├── vm-management.sh           # VM management utilities
├── development-tools.sh       # Development tools installer
├── docker-compose.yml         # Container definitions
├── README.md                  # This file
└── projects/                  # Development workspace
    └── AndroidDevTemplate/    # Sample project template
```

## Script Reference

### setup-android-dev.sh

Primary setup script that installs virtualization infrastructure and creates Android VM.

**Usage:**
```bash
./setup-android-dev.sh <android_iso_url>
```

**Features:**
- Installs KVM, libvirt, Docker, ADB
- Downloads and configures Android x86 ISO
- Creates VM with optimal settings
- Sets up networking and ADB connectivity
- Creates base snapshot for reset capability

### vm-management.sh

Comprehensive VM management with common operations.

**Commands:**
```bash
./vm-management.sh start       # Start VM
./vm-management.sh stop        # Stop VM  
./vm-management.sh restart     # Restart VM
./vm-management.sh status      # Show status
./vm-management.sh console     # Open console
./vm-management.sh reset       # Reset to clean state
./vm-management.sh snapshot    # Create snapshot
./vm-management.sh adb-connect # Connect ADB
./vm-management.sh install     # Install APK
./vm-management.sh ip          # Show VM IP
```

### development-tools.sh

Installs Android SDK, development tools, and utilities.

**Features:**
- Android SDK with latest platform tools
- Node.js and React Native CLI
- Testing frameworks and debugging tools
- Helper scripts for common tasks
- Project templates

## Android VM Configuration

### VM Specifications
- **Memory:** 8GB RAM
- **CPU:** 4 virtual cores
- **Storage:** 32GB qcow2 disk
- **Network:** NAT via libvirt default
- **Graphics:** SPICE with QXL video
- **Architecture:** x86_64

### Recommended Android Settings
1. Enable Developer Options
2. Enable USB Debugging
3. Enable ADB over network
4. Disable screen lock for testing
5. Set animation scales to 0.5x for faster UI

## Development Workflows

### Mobile App Testing

1. **Build APK:**
   ```bash
   cd your-project
   ./gradlew assembleDebug
   ```

2. **Install to VM:**
   ```bash
   ./vm-management.sh install app/build/outputs/apk/debug/app-debug.apk
   ```

3. **Debug with ADB:**
   ```bash
   adb logcat | grep YourApp
   ```

### React Native Development

1. **Setup project:**
   ```bash
   npx react-native init TestApp
   cd TestApp
   ```

2. **Build Android APK:**
   ```bash
   npx react-native run-android
   ```

3. **Connect to VM:**
   ```bash
   adb reverse tcp:8081 tcp:8081
   ```

### Automated Testing

1. **Appium setup:**
   ```bash
   npm install -g appium
   appium driver install uiautomator2
   ```

2. **Run tests:**
   ```bash
   python3 test_automation.py
   ```

## Snapshots and State Management

### Creating Snapshots
```bash
# Create named snapshot
./vm-management.sh snapshot "before-testing"

# Create automatic snapshot
virsh snapshot-create-as android-test auto-$(date +%Y%m%d-%H%M%S)
```

### Restoring State
```bash
# Reset to clean base state
./vm-management.sh reset

# Restore specific snapshot
virsh snapshot-revert android-test snapshot-name
```

### Managing Snapshots
```bash
# List snapshots
virsh snapshot-list android-test

# Delete snapshot
virsh snapshot-delete android-test snapshot-name
```

## Troubleshooting

### VM Won't Start
```bash
# Check virtualization support
grep -E '(vmx|svm)' /proc/cpuinfo

# Check libvirt status
sudo systemctl status libvirtd

# Check VM definition
virsh dumpxml android-test
```

### ADB Connection Issues
```bash
# Check VM IP
./vm-management.sh ip

# Test connectivity
ping <vm-ip>

# Restart ADB server
adb kill-server && adb start-server

# Connect manually
adb connect <vm-ip>:5555
```

### Performance Issues
```bash
# Check host resources
htop
df -h

# Optimize VM settings
virsh edit android-test
# Increase memory or CPU allocation

# Check disk space
virsh pool-list --details
```

### Network Problems
```bash
# Check libvirt network
virsh net-list --all
virsh net-info default

# Restart networking
sudo systemctl restart libvirtd
virsh net-destroy default
virsh net-start default
```

## Security Considerations

### VM Isolation
- VMs run in isolated KVM environment
- No access to host filesystem by default
- Network traffic goes through NAT

### Development Security
- Use snapshots for clean testing environments
- Don't install untrusted APKs on persistent state
- Regular VM resets prevent state accumulation

### Host Protection
- Keep host system updated
- Use non-root user for VM operations
- Monitor resource usage

## Performance Optimization

### Host Optimization
```bash
# Enable KVM nested virtualization
echo 'options kvm_intel nested=1' | sudo tee /etc/modprobe.d/kvm.conf

# Optimize CPU governor
sudo cpupower frequency-set -g performance

# Increase VM memory if available
virsh setmaxmem android-test 12G --config
virsh setmem android-test 12G --config
```

### VM Optimization
```bash
# Disable Android animations
adb shell settings put global window_animation_scale 0
adb shell settings put global transition_animation_scale 0
adb shell settings put global animator_duration_scale 0

# Reduce background processes
adb shell am kill-all
```

## Advanced Usage

### Custom VM Creation
```bash
# Create VM with different specs
virt-install \
  --name android-custom \
  --memory 16384 --vcpus 8 \
  --disk path=/var/lib/libvirt/images/android-custom.qcow2,size=64 \
  --cdrom android-x86.iso \
  --os-type linux --os-variant generic \
  --network network=default \
  --graphics spice --video qxl \
  --noautoconsole
```

### Port Forwarding
```bash
# Forward host port to VM
iptables -t nat -A PREROUTING -p tcp --dport 8080 -j DNAT --to-destination <vm-ip>:8080
```

### Multiple VMs
```bash
# Create additional test VMs
./setup-android-dev.sh android-iso-url
# Rename VM
virsh domrename android-test android-test-1

# Start multiple VMs
virsh start android-test-1
virsh start android-test-2
```

## Integration Examples

### CI/CD Pipeline
```yaml
# GitHub Actions example
- name: Setup Android VM
  run: |
    ./setup-android-dev.sh ${{ secrets.ANDROID_ISO_URL }}
    ./vm-management.sh start
    ./vm-management.sh adb-connect

- name: Run Tests
  run: |
    ./gradlew connectedAndroidTest
    ./vm-management.sh reset
```

### Docker Development
```bash
# Use containerized build environment
docker-compose run android-dev-tools bash
# Inside container:
sdkmanager --list
gradle build
```

## Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Submit pull request with detailed description

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
1. Check troubleshooting section
2. Review VM logs: `./vm-management.sh logs`
3. Create issue with system details and error messages