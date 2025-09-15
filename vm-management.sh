#!/bin/bash

# Android VM Management Script
# Provides convenient commands for managing Android x86 development VMs

VM_NAME="android-test"
ADB_PORT="5555"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_usage() {
    echo "Android VM Management Script"
    echo
    echo "Usage: $0 <command>"
    echo
    echo "Commands:"
    echo "  start       - Start the Android VM"
    echo "  stop        - Stop the Android VM"
    echo "  restart     - Restart the Android VM"
    echo "  status      - Show VM status"
    echo "  console     - Open VM console"
    echo "  reset       - Reset VM to clean state"
    echo "  snapshot    - Create a new snapshot"
    echo "  adb-connect - Connect ADB to VM"
    echo "  adb-status  - Show ADB connection status"
    echo "  install     - Install APK file"
    echo "  ip          - Show VM IP address"
    echo "  logs        - Show VM logs"
}

get_vm_ip() {
    virsh domifaddr "$VM_NAME" 2>/dev/null | grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' | head -1
}

vm_start() {
    log_info "Starting VM: $VM_NAME"
    if virsh list --state-running | grep -q "$VM_NAME"; then
        log_warn "VM is already running"
        return 0
    fi
    
    virsh start "$VM_NAME"
    log_info "VM started. Waiting for boot..."
    sleep 30
    
    local vm_ip
    vm_ip=$(get_vm_ip)
    if [[ -n "$vm_ip" ]]; then
        log_info "VM IP: $vm_ip"
    fi
}

vm_stop() {
    log_info "Stopping VM: $VM_NAME"
    if ! virsh list --state-running | grep -q "$VM_NAME"; then
        log_warn "VM is not running"
        return 0
    fi
    
    virsh shutdown "$VM_NAME"
    log_info "Shutdown command sent"
}

vm_restart() {
    log_info "Restarting VM: $VM_NAME"
    vm_stop
    sleep 10
    vm_start
}

vm_status() {
    echo -e "${BLUE}VM Status:${NC}"
    virsh list --all | grep "$VM_NAME" || echo "VM not found"
    echo
    
    if virsh list --state-running | grep -q "$VM_NAME"; then
        local vm_ip
        vm_ip=$(get_vm_ip)
        echo -e "${BLUE}Network:${NC}"
        echo "IP Address: ${vm_ip:-Unknown}"
        echo
        
        echo -e "${BLUE}ADB Status:${NC}"
        adb devices | grep -E "(connected|device)" || echo "No ADB devices connected"
    fi
}

vm_console() {
    log_info "Opening VM console"
    if ! virsh list --state-running | grep -q "$VM_NAME"; then
        log_error "VM is not running. Start it first with: $0 start"
        return 1
    fi
    
    virt-viewer "$VM_NAME" &
}

vm_reset() {
    log_warn "Resetting VM to clean state"
    read -p "This will lose any changes made to the VM. Continue? (y/N): " confirm
    if [[ $confirm != [yY] ]]; then
        log_info "Reset cancelled"
        return 0
    fi
    
    vm_stop
    sleep 5
    virsh snapshot-revert "$VM_NAME" clean-state
    log_info "VM reset to clean state"
}

vm_snapshot() {
    local snapshot_name="$1"
    if [[ -z "$snapshot_name" ]]; then
        snapshot_name="manual-$(date +%Y%m%d-%H%M%S)"
    fi
    
    log_info "Creating snapshot: $snapshot_name"
    virsh snapshot-create-as "$VM_NAME" "$snapshot_name" "Manual snapshot created $(date)"
    log_info "Snapshot created successfully"
}

adb_connect() {
    local vm_ip
    vm_ip=$(get_vm_ip)
    
    if [[ -z "$vm_ip" ]]; then
        log_error "Cannot determine VM IP address. Is the VM running?"
        return 1
    fi
    
    log_info "Connecting ADB to $vm_ip:$ADB_PORT"
    adb connect "$vm_ip:$ADB_PORT"
}

adb_status() {
    echo -e "${BLUE}ADB Devices:${NC}"
    adb devices
    echo
    
    echo -e "${BLUE}Connected to VM:${NC}"
    local vm_ip
    vm_ip=$(get_vm_ip)
    if [[ -n "$vm_ip" ]] && adb devices | grep -q "$vm_ip:$ADB_PORT"; then
        echo -e "${GREEN}✓${NC} Connected to $vm_ip:$ADB_PORT"
    else
        echo -e "${RED}✗${NC} Not connected to VM"
    fi
}

install_apk() {
    local apk_file="$1"
    if [[ -z "$apk_file" ]]; then
        log_error "APK file not specified"
        echo "Usage: $0 install <path_to_apk>"
        return 1
    fi
    
    if [[ ! -f "$apk_file" ]]; then
        log_error "APK file not found: $apk_file"
        return 1
    fi
    
    log_info "Installing APK: $apk_file"
    adb install "$apk_file"
}

show_vm_ip() {
    local vm_ip
    vm_ip=$(get_vm_ip)
    
    if [[ -n "$vm_ip" ]]; then
        echo "VM IP: $vm_ip"
    else
        echo "VM IP: Not available (VM may not be running)"
    fi
}

show_vm_logs() {
    log_info "Showing VM logs"
    virsh dumpxml "$VM_NAME" | grep -E "(log|serial)" || echo "No log configuration found"
    echo
    journalctl -u libvirtd | tail -20
}

# Main command processing
case "$1" in
    start)
        vm_start
        ;;
    stop)
        vm_stop
        ;;
    restart)
        vm_restart
        ;;
    status)
        vm_status
        ;;
    console)
        vm_console
        ;;
    reset)
        vm_reset
        ;;
    snapshot)
        vm_snapshot "$2"
        ;;
    adb-connect)
        adb_connect
        ;;
    adb-status)
        adb_status
        ;;
    install)
        install_apk "$2"
        ;;
    ip)
        show_vm_ip
        ;;
    logs)
        show_vm_logs
        ;;
    *)
        show_usage
        exit 1
        ;;
esac