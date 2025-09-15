#!/bin/bash
# Phase 14A QA Emulation Framework - Dependency Installation
# This script installs all required dependencies for the mobile QA testing framework

set -euo pipefail

echo "=== Phase 14A QA Framework - Installing Dependencies ==="

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root for system package installation"
   echo "Usage: sudo $0"
   exit 1
fi

# Update package manager
echo "Updating package manager..."
apt-get update -y

# Install virtualization and containerization tools
echo "Installing virtualization and container tools..."
apt-get install -y \
    qemu-kvm \
    libvirt-clients \
    libvirt-daemon-system \
    virtinst \
    virt-manager \
    docker.io \
    docker-compose \
    bridge-utils

# Install development and automation tools
echo "Installing development tools..."
apt-get install -y \
    git \
    curl \
    jq \
    imagemagick \
    ffmpeg \
    bc \
    redis-tools \
    python3 \
    python3-pip \
    python3-dev \
    nodejs \
    npm

# Install Android development tools
echo "Installing Android development tools..."
apt-get install -y \
    android-tools-adb \
    android-tools-fastboot

# Install Python packages
echo "Installing Python packages..."
pip3 install --upgrade pip
pip3 install \
    requests \
    numpy \
    bezier \
    opencv-python \
    pillow \
    redis \
    aiohttp \
    asyncio \
    pytest \
    pytest-asyncio \
    psutil \
    pyyaml

# Install kubectl for autoscaling
echo "Installing kubectl..."
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Setup Docker group and permissions
echo "Setting up Docker permissions..."
groupadd -f docker
usermod -aG libvirt $SUDO_USER
usermod -aG docker $SUDO_USER

# Enable and start services
echo "Enabling services..."
systemctl enable libvirtd
systemctl start libvirtd
systemctl enable docker
systemctl start docker
systemctl enable redis-server
systemctl start redis-server

# Create required directories
echo "Creating directories..."
mkdir -p /opt/qa-framework/{vm-templates,scripts,logs,data}
mkdir -p /var/log/qa-framework
chown -R $SUDO_USER:$SUDO_USER /opt/qa-framework

# Verify installations
echo "Verifying installations..."
echo "Docker version: $(docker --version)"
echo "Python version: $(python3 --version)"
echo "ADB version: $(adb --version)"
echo "KVM support: $(kvm-ok || echo 'KVM not available')"

echo "=== Dependencies installation completed successfully ==="
echo "Note: You may need to log out and back in for group permissions to take effect."