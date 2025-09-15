#!/bin/bash

# Android x86 Development Environment Setup
# Sets up virtualization infrastructure for Android app testing and development

set -e

# Configuration
ANDROID_ISO_URL="${1:-}"
VM_NAME="android-test"
VM_MEMORY="8192"
VM_VCPUS="4"
VM_DISK_SIZE="32"
ADB_PORT="5555"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_requirements() {
    log_info "Checking system requirements..."
    
    # Check if running on Ubuntu/Debian
    if ! command -v apt &> /dev/null; then
        log_error "This script requires Ubuntu/Debian with apt package manager"
        exit 1
    fi
    
    # Check virtualization support
    if ! grep -q -E '(vmx|svm)' /proc/cpuinfo; then
        log_error "CPU virtualization not supported or not enabled in BIOS"
        exit 1
    fi
    
    # Check if running as non-root
    if [[ $EUID -eq 0 ]]; then
        log_error "Do not run this script as root"
        exit 1
    fi
    
    log_info "System requirements check passed"
}

install_host_dependencies() {
    log_info "Installing host dependencies..."
    
    sudo apt update
    sudo apt install -y \
        qemu-kvm \
        libvirt-daemon-system \
        libvirt-clients \
        bridge-utils \
        virt-manager \
        docker.io \
        android-tools-adb \
        android-tools-fastboot \
        git \
        python3-pip \
        nodejs \
        npm \
        curl \
        wget \
        unzip
    
    # Add user to required groups
    sudo usermod -aG libvirt,docker "$USER"
    
    # Enable services
    sudo systemctl enable --now libvirtd
    sudo systemctl enable --now docker
    
    log_info "Host dependencies installed successfully"
}

verify_android_iso() {
    if [[ -z "$ANDROID_ISO_URL" ]]; then
        log_error "Android ISO URL not provided"
        echo "Usage: $0 <android_iso_url>"
        echo "Example: $0 https://osdn.net/projects/android-x86/downloads/71931/android-x86_64-9.0-r2.iso"
        exit 1
    fi
    
    log_info "Verifying Android ISO URL: $ANDROID_ISO_URL"
    
    if ! curl -I "$ANDROID_ISO_URL" &>/dev/null; then
        log_error "Cannot access Android ISO URL"
        exit 1
    fi
    
    log_info "Android ISO URL verified"
}

download_android_iso() {
    local iso_filename
    iso_filename=$(basename "$ANDROID_ISO_URL")
    local iso_path="/tmp/$iso_filename"
    
    if [[ ! -f "$iso_path" ]]; then
        log_info "Downloading Android ISO..."
        wget -O "$iso_path" "$ANDROID_ISO_URL"
    else
        log_info "Android ISO already downloaded"
    fi
    
    echo "$iso_path"
}

create_android_vm() {
    local iso_path="$1"
    
    log_info "Creating Android VM: $VM_NAME"
    
    # Check if VM already exists
    if virsh list --all | grep -q "$VM_NAME"; then
        log_warn "VM $VM_NAME already exists. Removing..."
        virsh destroy "$VM_NAME" 2>/dev/null || true
        virsh undefine "$VM_NAME" --remove-all-storage 2>/dev/null || true
    fi
    
    # Create VM
    virt-install \
        --name "$VM_NAME" \
        --memory "$VM_MEMORY" \
        --vcpus "$VM_VCPUS" \
        --disk path="/var/lib/libvirt/images/${VM_NAME}.qcow2,size=$VM_DISK_SIZE,format=qcow2" \
        --cdrom "$iso_path" \
        --os-type linux \
        --os-variant generic \
        --network network=default \
        --graphics spice,listen=0.0.0.0 \
        --video qxl \
        --console pty,target_type=serial \
        --boot cdrom,hd \
        --noautoconsole
    
    log_info "VM created successfully"
}

create_base_snapshot() {
    log_info "Creating base snapshot..."
    
    # Wait for VM to be defined
    sleep 5
    
    # Create snapshot
    virsh snapshot-create-as "$VM_NAME" clean-state "Initial clean state after installation" --atomic
    
    log_info "Base snapshot created"
}

setup_networking() {
    log_info "Setting up VM networking for ADB..."
    
    # Start VM if not running
    if ! virsh list --state-running | grep -q "$VM_NAME"; then
        virsh start "$VM_NAME"
        log_info "VM started, waiting for boot..."
        sleep 60
    fi
    
    # Get VM IP address
    local vm_ip
    vm_ip=$(virsh domifaddr "$VM_NAME" | grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' | head -1)
    
    if [[ -n "$vm_ip" ]]; then
        log_info "VM IP address: $vm_ip"
        echo "VM_IP=$vm_ip" > /tmp/android-vm-config
    else
        log_warn "Could not determine VM IP address"
        log_info "You may need to manually configure ADB connection"
    fi
}

test_adb_connection() {
    log_info "Testing ADB connection..."
    
    # Try to connect to VM
    if [[ -f /tmp/android-vm-config ]]; then
        source /tmp/android-vm-config
        if [[ -n "$VM_IP" ]]; then
            log_info "Attempting ADB connection to $VM_IP:$ADB_PORT"
            adb connect "$VM_IP:$ADB_PORT" || log_warn "ADB connection failed - Android may not be fully booted yet"
        fi
    fi
    
    # Show connected devices
    adb devices
}

install_development_tools() {
    log_info "Installing additional development tools..."
    
    # Install Android Studio command line tools
    local tools_dir="$HOME/android-sdk"
    mkdir -p "$tools_dir"
    
    # Download command line tools
    local tools_url="https://dl.google.com/android/repository/commandlinetools-linux-8512546_latest.zip"
    local tools_zip="/tmp/commandlinetools.zip"
    
    if [[ ! -f "$tools_zip" ]]; then
        wget -O "$tools_zip" "$tools_url"
    fi
    
    unzip -o "$tools_zip" -d "$tools_dir"
    
    # Set up environment
    {
        echo "export ANDROID_HOME=$tools_dir"
        echo "export PATH=\$PATH:\$ANDROID_HOME/cmdline-tools/bin:\$ANDROID_HOME/platform-tools"
    } >> "$HOME/.bashrc"
    
    log_info "Development tools installed"
}

create_usage_guide() {
    local guide_file="$HOME/android-dev-guide.txt"
    
    cat > "$guide_file" << 'EOF'
Android x86 Development Environment Usage Guide
===============================================

VM Management:
  Start VM:    virsh start android-test
  Stop VM:     virsh shutdown android-test
  Reset VM:    virsh snapshot-revert android-test clean-state
  
ADB Commands:
  Connect:     adb connect <VM_IP>:5555
  Devices:     adb devices
  Shell:       adb shell
  Install APK: adb install app.apk
  
VM Console:
  Access:      virt-viewer android-test
  
Development:
  - Use Android Studio or VS Code for development
  - Test apps by installing APKs via ADB
  - Use VM snapshots for clean testing environments
  
Troubleshooting:
  - If ADB fails to connect, ensure Android is fully booted
  - Enable Developer Options and USB Debugging in Android
  - Check VM IP with: virsh domifaddr android-test
  
EOF

    log_info "Usage guide created at $guide_file"
}

main() {
    log_info "Starting Android x86 Development Environment Setup"
    
    check_requirements
    verify_android_iso
    install_host_dependencies
    
    local iso_path
    iso_path=$(download_android_iso)
    
    create_android_vm "$iso_path"
    create_base_snapshot
    setup_networking
    install_development_tools
    create_usage_guide
    
    log_info "Setup completed successfully!"
    echo
    echo "Next steps:"
    echo "1. Reboot or log out/in to apply group membership changes"
    echo "2. Open virt-viewer android-test to access VM console"
    echo "3. Install Android and enable Developer Options"
    echo "4. Use 'adb connect <VM_IP>:5555' to connect ADB"
    echo "5. Read ~/android-dev-guide.txt for usage instructions"
}

# Show usage if no arguments
if [[ $# -eq 0 ]]; then
    echo "Usage: $0 <android_iso_url>"
    echo
    echo "Example Android x86 ISOs:"
    echo "  Android 9.0:  https://osdn.net/projects/android-x86/downloads/71931/android-x86_64-9.0-r2.iso"
    echo "  Android 11.0: https://osdn.net/projects/android-x86/downloads/75636/android-x86_64-11.0-r4.iso"
    exit 1
fi

main "$@"