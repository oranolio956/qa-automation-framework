#!/bin/bash
# VM Provisioning Script for QA Framework
# Provisions and configures Android VMs for testing

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$SCRIPT_DIR/../config"
TEMPLATE_DIR="$SCRIPT_DIR/../templates"

# Default configuration
VM_COUNT=${1:-3}
VM_PREFIX="qa-android"
VM_RAM="4096"
VM_DISK="20G"
ANDROID_IMAGE_URL="https://osdn.net/frs/redir.php?m=acc&f=android-x86%2F71931%2Fandroid-x86_64-9.0-r2.iso"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

create_vm_template() {
    local vm_name="$1"
    local vm_id="$2"
    
    log "Creating VM template for $vm_name..."
    
    # Create VM XML configuration
    cat > "$TEMPLATE_DIR/${vm_name}.xml" << EOF
<domain type='kvm'>
  <name>$vm_name</name>
  <uuid>$(uuidgen)</uuid>
  <memory unit='KiB'>$(($VM_RAM * 1024))</memory>
  <currentMemory unit='KiB'>$(($VM_RAM * 1024))</currentMemory>
  <vcpu placement='static'>2</vcpu>
  <os>
    <type arch='x86_64' machine='pc-i440fx-2.12'>hvm</type>
    <boot dev='cdrom'/>
    <boot dev='hd'/>
  </os>
  <features>
    <acpi/>
    <apic/>
    <vmport state='off'/>
  </features>
  <cpu mode='host-model' check='partial'>
    <model fallback='allow'/>
  </cpu>
  <clock offset='utc'>
    <timer name='rtc' tickpolicy='catchup'/>
    <timer name='pit' tickpolicy='delay'/>
    <timer name='hpet' present='no'/>
  </clock>
  <on_poweroff>destroy</on_poweroff>
  <on_reboot>restart</on_reboot>
  <on_crash>destroy</on_crash>
  <pm>
    <suspend-to-mem enabled='no'/>
    <suspend-to-disk enabled='no'/>
  </pm>
  <devices>
    <emulator>/usr/bin/qemu-system-x86_64</emulator>
    <disk type='file' device='disk'>
      <driver name='qemu' type='qcow2'/>
      <source file='/var/lib/libvirt/images/${vm_name}.qcow2'/>
      <target dev='vda' bus='virtio'/>
    </disk>
    <disk type='file' device='cdrom'>
      <driver name='qemu' type='raw'/>
      <source file='/var/lib/libvirt/images/android-x86.iso'/>
      <target dev='hdc' bus='ide'/>
      <readonly/>
    </disk>
    <controller type='usb' index='0' model='ich9-ehci1'/>
    <controller type='usb' index='0' model='ich9-uhci1'>
      <master startport='0'/>
    </controller>
    <controller type='usb' index='0' model='ich9-uhci2'>
      <master startport='2'/>
    </controller>
    <controller type='usb' index='0' model='ich9-uhci3'>
      <master startport='4'/>
    </controller>
    <controller type='pci' index='0' model='pci-root'/>
    <controller type='ide' index='0'/>
    <controller type='virtio-serial' index='0'/>
    <interface type='network'>
      <mac address='52:54:00:$(printf "%02x:%02x:%02x" $((RANDOM%256)) $((RANDOM%256)) $((RANDOM%256)))'/>
      <source network='default'/>
      <model type='virtio'/>
    </interface>
    <serial type='pty'>
      <target type='isa-serial' port='0'>
        <model name='isa-serial'/>
      </target>
    </serial>
    <console type='pty'>
      <target type='serial' port='0'/>
    </console>
    <channel type='unix'>
      <target type='virtio' name='org.qemu.guest_agent.0'/>
    </channel>
    <input type='tablet' bus='usb'/>
    <input type='mouse' bus='ps2'/>
    <input type='keyboard' bus='ps2'/>
    <graphics type='vnc' port='-1' autoport='yes' listen='0.0.0.0'>
      <listen type='address' address='0.0.0.0'/>
    </graphics>
    <sound model='ich6'>
      <audio id='1'/>
    </sound>
    <audio id='1' type='none'/>
    <video>
      <model type='cirrus' vram='16384' heads='1' primary='yes'/>
    </video>
    <memballoon model='virtio'/>
  </devices>
</domain>
EOF
}

download_android_image() {
    log "Downloading Android x86 image..."
    if [ ! -f "/var/lib/libvirt/images/android-x86.iso" ]; then
        wget -O "/var/lib/libvirt/images/android-x86.iso" "$ANDROID_IMAGE_URL"
    else
        log "Android image already exists"
    fi
}

create_vm_disk() {
    local vm_name="$1"
    log "Creating disk for $vm_name..."
    qemu-img create -f qcow2 "/var/lib/libvirt/images/${vm_name}.qcow2" "$VM_DISK"
}

provision_vms() {
    log "Provisioning $VM_COUNT VMs..."
    
    # Download Android image
    download_android_image
    
    # Create VMs
    for i in $(seq 1 $VM_COUNT); do
        vm_name="${VM_PREFIX}-$(printf "%02d" $i)"
        
        log "Provisioning VM: $vm_name"
        
        # Create VM template
        create_vm_template "$vm_name" "$i"
        
        # Create disk
        create_vm_disk "$vm_name"
        
        # Define VM in libvirt
        virsh define "$TEMPLATE_DIR/${vm_name}.xml"
        
        # Set VM to autostart
        virsh autostart "$vm_name"
        
        log "VM $vm_name provisioned successfully"
    done
}

optimize_host_resources() {
    log "Optimizing host resources for VM pool..."
    
    # Enable KSM (Kernel Same-page Merging) for memory deduplication
    echo 1 > /sys/kernel/mm/ksm/run
    echo 500 > /sys/kernel/mm/ksm/pages_to_scan
    
    # Configure VM templates for headless operation
    for vm_xml in "$TEMPLATE_DIR"/*.xml; do
        if [ -f "$vm_xml" ]; then
            # Modify graphics to headless
            sed -i 's/<graphics type="vnc".*/<graphics type="none"\/>/' "$vm_xml"
            # Update the VM definition
            virsh define "$vm_xml"
        fi
    done
    
    log "Host resource optimization completed"
}

main() {
    log "Starting VM provisioning for QA framework..."
    
    # Create required directories
    mkdir -p "$TEMPLATE_DIR" "$CONFIG_DIR" /var/log/qa-framework
    
    # Provision VMs
    provision_vms
    
    # Optimize resources
    optimize_host_resources
    
    log "VM provisioning completed successfully"
    log "Created $VM_COUNT VMs with prefix: $VM_PREFIX"
    
    # List created VMs
    log "Available VMs:"
    virsh list --all | grep "$VM_PREFIX"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root"
   exit 1
fi

main "$@"