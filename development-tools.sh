#!/bin/bash

# Android Development Tools Setup
# Installs and configures Android SDK, development tools, and utilities

set -e

# Configuration
ANDROID_SDK_ROOT="$HOME/Android/Sdk"
ANDROID_TOOLS_VERSION="8512546"
GRADLE_VERSION="7.6"
NODE_VERSION="18"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
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

install_android_sdk() {
    log_info "Installing Android SDK..."
    
    # Create SDK directory
    mkdir -p "$ANDROID_SDK_ROOT"
    
    # Download command line tools
    local tools_url="https://dl.google.com/android/repository/commandlinetools-linux-${ANDROID_TOOLS_VERSION}_latest.zip"
    local temp_zip="/tmp/commandlinetools.zip"
    
    if [[ ! -f "$temp_zip" ]]; then
        log_info "Downloading Android command line tools..."
        wget -O "$temp_zip" "$tools_url"
    fi
    
    # Extract tools
    unzip -o "$temp_zip" -d "$ANDROID_SDK_ROOT"
    
    # Move to correct location
    if [[ ! -d "$ANDROID_SDK_ROOT/cmdline-tools/latest" ]]; then
        mkdir -p "$ANDROID_SDK_ROOT/cmdline-tools/latest"
        mv "$ANDROID_SDK_ROOT/cmdline-tools/bin" "$ANDROID_SDK_ROOT/cmdline-tools/latest/"
        mv "$ANDROID_SDK_ROOT/cmdline-tools/lib" "$ANDROID_SDK_ROOT/cmdline-tools/latest/"
        mv "$ANDROID_SDK_ROOT/cmdline-tools"/*.txt "$ANDROID_SDK_ROOT/cmdline-tools/latest/" 2>/dev/null || true
        mv "$ANDROID_SDK_ROOT/cmdline-tools"/*.properties "$ANDROID_SDK_ROOT/cmdline-tools/latest/" 2>/dev/null || true
    fi
    
    # Set up environment
    export ANDROID_HOME="$ANDROID_SDK_ROOT"
    export PATH="$PATH:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools"
    
    log_info "Android SDK installed"
}

install_sdk_packages() {
    log_info "Installing Android SDK packages..."
    
    # Accept licenses
    yes | sdkmanager --licenses >/dev/null 2>&1 || true
    
    # Install essential packages
    sdkmanager --install \
        "platform-tools" \
        "platforms;android-33" \
        "platforms;android-32" \
        "platforms;android-31" \
        "build-tools;33.0.2" \
        "build-tools;32.0.0" \
        "system-images;android-33;google_apis;x86_64" \
        "emulator"
    
    log_info "SDK packages installed"
}

setup_environment() {
    log_info "Setting up environment variables..."
    
    # Add to bashrc
    {
        echo ""
        echo "# Android Development Environment"
        echo "export ANDROID_HOME=\"$ANDROID_SDK_ROOT\""
        echo "export ANDROID_SDK_ROOT=\"$ANDROID_SDK_ROOT\""
        echo "export PATH=\"\$PATH:\$ANDROID_HOME/cmdline-tools/latest/bin:\$ANDROID_HOME/platform-tools:\$ANDROID_HOME/emulator\""
    } >> "$HOME/.bashrc"
    
    # Add to profile for non-bash shells
    {
        echo ""
        echo "# Android Development Environment"
        echo "export ANDROID_HOME=\"$ANDROID_SDK_ROOT\""
        echo "export ANDROID_SDK_ROOT=\"$ANDROID_SDK_ROOT\""
        echo "export PATH=\"\$PATH:\$ANDROID_HOME/cmdline-tools/latest/bin:\$ANDROID_HOME/platform-tools:\$ANDROID_HOME/emulator\""
    } >> "$HOME/.profile"
    
    log_info "Environment variables configured"
}

install_nodejs_tools() {
    log_info "Installing Node.js development tools..."
    
    # Install nvm if not present
    if ! command -v nvm &> /dev/null; then
        curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
        export NVM_DIR="$HOME/.nvm"
        [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    fi
    
    # Install and use Node.js
    nvm install "$NODE_VERSION"
    nvm use "$NODE_VERSION"
    
    # Install React Native CLI and other tools
    npm install -g \
        @react-native-community/cli \
        react-native-debugger \
        flipper-pkg \
        appium \
        cordova \
        ionic
    
    log_info "Node.js tools installed"
}

install_testing_tools() {
    log_info "Installing testing and debugging tools..."
    
    # Python tools
    pip3 install --user \
        appium-python-client \
        pytest \
        requests \
        selenium \
        frida-tools
    
    # Install additional debugging tools
    sudo apt install -y \
        wireshark \
        tcpdump \
        htop \
        iftop \
        strace \
        ltrace
    
    log_info "Testing tools installed"
}

create_dev_scripts() {
    log_info "Creating development scripts..."
    
    # ADB helper script
    cat > "$HOME/bin/adb-helper.sh" << 'EOF'
#!/bin/bash

# ADB Helper Script

case "$1" in
    devices)
        echo "Connected devices:"
        adb devices -l
        ;;
    install)
        if [[ -n "$2" ]]; then
            echo "Installing $2..."
            adb install -r "$2"
        else
            echo "Usage: $0 install <apk_file>"
        fi
        ;;
    screenshot)
        local filename="${2:-screenshot-$(date +%Y%m%d-%H%M%S).png}"
        echo "Taking screenshot: $filename"
        adb exec-out screencap -p > "$filename"
        ;;
    logs)
        echo "Showing logcat..."
        adb logcat -c
        adb logcat
        ;;
    shell)
        adb shell
        ;;
    *)
        echo "Usage: $0 {devices|install|screenshot|logs|shell}"
        ;;
esac
EOF

    # Make executable
    mkdir -p "$HOME/bin"
    chmod +x "$HOME/bin/adb-helper.sh"
    
    # Gradle wrapper script
    cat > "$HOME/bin/gradle-helper.sh" << 'EOF'
#!/bin/bash

# Gradle Helper Script

PROJECT_DIR="${2:-.}"

case "$1" in
    clean)
        echo "Cleaning project..."
        cd "$PROJECT_DIR" && ./gradlew clean
        ;;
    build)
        echo "Building project..."
        cd "$PROJECT_DIR" && ./gradlew build
        ;;
    test)
        echo "Running tests..."
        cd "$PROJECT_DIR" && ./gradlew test
        ;;
    debug)
        echo "Building debug APK..."
        cd "$PROJECT_DIR" && ./gradlew assembleDebug
        ;;
    release)
        echo "Building release APK..."
        cd "$PROJECT_DIR" && ./gradlew assembleRelease
        ;;
    *)
        echo "Usage: $0 {clean|build|test|debug|release} [project_dir]"
        ;;
esac
EOF

    chmod +x "$HOME/bin/gradle-helper.sh"
    
    log_info "Development scripts created"
}

verify_installation() {
    log_info "Verifying installation..."
    
    # Source environment
    export ANDROID_HOME="$ANDROID_SDK_ROOT"
    export PATH="$PATH:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools"
    
    echo "Checking tools..."
    
    # Check ADB
    if command -v adb &> /dev/null; then
        echo "✓ ADB: $(adb --version | head -1)"
    else
        echo "✗ ADB not found"
    fi
    
    # Check SDK Manager
    if command -v sdkmanager &> /dev/null; then
        echo "✓ SDK Manager available"
    else
        echo "✗ SDK Manager not found"
    fi
    
    # Check Node.js
    if command -v node &> /dev/null; then
        echo "✓ Node.js: $(node --version)"
    else
        echo "✗ Node.js not found"
    fi
    
    # Check NPM packages
    if command -v react-native &> /dev/null; then
        echo "✓ React Native CLI available"
    else
        echo "✗ React Native CLI not found"
    fi
    
    log_info "Verification complete"
}

create_project_template() {
    local template_dir="$HOME/AndroidDevTemplate"
    
    log_info "Creating project template..."
    
    mkdir -p "$template_dir"
    
    # Create basic Android project structure
    cat > "$template_dir/build.gradle" << 'EOF'
// Top-level build file
buildscript {
    ext.kotlin_version = '1.8.0'
    dependencies {
        classpath 'com.android.tools.build:gradle:7.4.0'
        classpath "org.jetbrains.kotlin:kotlin-gradle-plugin:$kotlin_version"
    }
}

allprojects {
    repositories {
        google()
        mavenCentral()
    }
}
EOF

    # Create app-level build.gradle
    mkdir -p "$template_dir/app"
    cat > "$template_dir/app/build.gradle" << 'EOF'
apply plugin: 'com.android.application'
apply plugin: 'kotlin-android'

android {
    compileSdkVersion 33
    
    defaultConfig {
        applicationId "com.example.testapp"
        minSdkVersion 21
        targetSdkVersion 33
        versionCode 1
        versionName "1.0"
        testInstrumentationRunner "androidx.test.runner.AndroidJUnitRunner"
    }
    
    buildTypes {
        release {
            minifyEnabled false
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
        }
    }
}

dependencies {
    implementation 'androidx.core:core-ktx:1.9.0'
    implementation 'androidx.appcompat:appcompat:1.6.0'
    implementation 'com.google.android.material:material:1.7.0'
    testImplementation 'junit:junit:4.13.2'
    androidTestImplementation 'androidx.test.ext:junit:1.1.5'
    androidTestImplementation 'androidx.test.espresso:espresso-core:3.5.1'
}
EOF

    # Create README
    cat > "$template_dir/README.md" << 'EOF'
# Android Development Template

This template provides a basic Android project structure for development and testing.

## Usage

1. Copy this template to your project directory
2. Update package names and app configuration
3. Run `./gradlew build` to build the project
4. Use ADB to install and test on Android x86 VM

## Development Commands

- `./gradlew clean` - Clean build
- `./gradlew assembleDebug` - Build debug APK
- `adb install -r app/build/outputs/apk/debug/app-debug.apk` - Install APK
- `adb logcat` - View logs

EOF

    log_info "Project template created at $template_dir"
}

main() {
    log_info "Starting Android development tools installation"
    
    install_android_sdk
    install_sdk_packages
    setup_environment
    install_nodejs_tools
    install_testing_tools
    create_dev_scripts
    create_project_template
    verify_installation
    
    log_info "Installation completed successfully!"
    echo
    echo "Next steps:"
    echo "1. Restart your terminal or run: source ~/.bashrc"
    echo "2. Verify installation: adb --version"
    echo "3. Use helper scripts in ~/bin/ for common tasks"
    echo "4. Project template available at ~/AndroidDevTemplate"
}

main "$@"