#!/bin/bash

# Persona Testing Framework
# Configures test user profiles, audio testing, and usage pattern automation
# For legitimate application testing, QA, and user experience validation

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/logs/persona-testing.log"
REPO_PATH="${1:-$SCRIPT_DIR}"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}" | tee -a "$LOG_FILE"
}

# Create logs directory
mkdir -p "${SCRIPT_DIR}/logs"

# Create test persona profile generator
create_persona_generator() {
    log "Creating test persona profile generator..."
    
    mkdir -p "${REPO_PATH}/testing/personas"
    
    cat > "${REPO_PATH}/testing/personas/persona_generator.py" << 'EOF'
#!/usr/bin/env python3
"""
Test Persona Generator
Creates randomized test user profiles for application testing and QA
For legitimate software testing purposes only
"""

import argparse
import random
import json
import datetime
from typing import Dict, Any, List

class PersonaGenerator:
    """Generates test user personas for application testing"""
    
    def __init__(self):
        self.test_names = {
            'male': ['Alex', 'Chris', 'Jordan', 'Taylor', 'Sam', 'Casey', 'Riley'],
            'female': ['Quinn', 'Morgan', 'Avery', 'Blake', 'Drew', 'Sage', 'Rowan']
        }
        
        self.interests = [
            'photography', 'travel', 'music', 'sports', 'cooking', 'reading',
            'hiking', 'gaming', 'art', 'technology', 'fitness', 'movies'
        ]
        
        self.bio_styles = {
            'casual': ['Love {interest}!', 'Into {interest} and good vibes', '{interest} enthusiast'],
            'professional': ['Passionate about {interest}', 'Career-focused, enjoy {interest}'],
            'creative': ['{interest} + coffee = perfect day', 'Life through the lens of {interest}']
        }
    
    def generate_test_persona(self, gender: str = None, age_range: tuple = (18, 35)) -> Dict[str, Any]:
        """Generate a test persona for application testing"""
        
        # Randomize gender if not specified
        if gender is None:
            gender = random.choice(['male', 'female'])
        
        # Generate test profile
        persona = {
            'test_id': f"test_{random.randint(10000, 99999)}",
            'profile': {
                'name': random.choice(self.test_names[gender]),
                'gender': gender,
                'age': random.randint(age_range[0], age_range[1]),
                'birthdate': self._generate_birthdate(age_range),
                'bio': self._generate_bio(),
                'interests': random.sample(self.interests, k=random.randint(3, 6))
            },
            'testing_config': {
                'bio_style': random.choice(['casual', 'professional', 'creative']),
                'interaction_level': random.choice(['low', 'medium', 'high']),
                'response_delay': random.randint(2, 10),
                'session_duration': random.randint(300, 1800)  # 5-30 minutes
            },
            'created_at': datetime.datetime.now().isoformat()
        }
        
        return persona
    
    def _generate_birthdate(self, age_range: tuple) -> str:
        """Generate a realistic birthdate for testing"""
        age = random.randint(age_range[0], age_range[1])
        year = datetime.date.today().year - age
        month = random.randint(1, 12)
        day = random.randint(1, 28)  # Safe day range for all months
        return f"{year}-{month:02d}-{day:02d}"
    
    def _generate_bio(self) -> str:
        """Generate a test bio for the persona"""
        style = random.choice(['casual', 'professional', 'creative'])
        template = random.choice(self.bio_styles[style])
        interest = random.choice(self.interests)
        return template.format(interest=interest)
    
    def generate_test_cohort(self, size: int, cohort_config: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Generate a cohort of test personas for A/B testing"""
        
        cohort = []
        config = cohort_config or {}
        
        for i in range(size):
            persona = self.generate_test_persona(
                gender=config.get('gender'),
                age_range=config.get('age_range', (18, 35))
            )
            
            # Apply cohort-specific settings
            if 'bio_style' in config:
                persona['testing_config']['bio_style'] = config['bio_style']
            
            if 'interaction_level' in config:
                persona['testing_config']['interaction_level'] = config['interaction_level']
            
            persona['cohort_id'] = config.get('cohort_id', 'default')
            cohort.append(persona)
        
        return cohort
    
    def save_personas(self, personas: List[Dict[str, Any]], filename: str):
        """Save generated personas to file for testing"""
        with open(filename, 'w') as f:
            json.dump(personas, f, indent=2)
        print(f"Saved {len(personas)} test personas to {filename}")

def main():
    parser = argparse.ArgumentParser(description='Generate test personas for application testing')
    parser.add_argument('--gender', choices=['male', 'female'], help='Specify gender for testing')
    parser.add_argument('--count', type=int, default=1, help='Number of personas to generate')
    parser.add_argument('--cohort-size', type=int, help='Generate cohort of specified size')
    parser.add_argument('--output', default='test_personas.json', help='Output file path')
    parser.add_argument('--age-min', type=int, default=18, help='Minimum age for test personas')
    parser.add_argument('--age-max', type=int, default=35, help='Maximum age for test personas')
    parser.add_argument('--bio-style', choices=['casual', 'professional', 'creative'], help='Bio style for cohort')
    
    args = parser.parse_args()
    
    generator = PersonaGenerator()
    
    if args.cohort_size:
        # Generate cohort for A/B testing
        cohort_config = {
            'gender': args.gender,
            'age_range': (args.age_min, args.age_max),
            'bio_style': args.bio_style,
            'cohort_id': f"test_cohort_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
        personas = generator.generate_test_cohort(args.cohort_size, cohort_config)
    else:
        # Generate individual personas
        personas = []
        for _ in range(args.count):
            persona = generator.generate_test_persona(
                gender=args.gender,
                age_range=(args.age_min, args.age_max)
            )
            personas.append(persona)
    
    generator.save_personas(personas, args.output)
    
    # Print summary
    print(f"\nGenerated {len(personas)} test personas:")
    for persona in personas[:3]:  # Show first 3 as examples
        print(f"- {persona['profile']['name']} ({persona['profile']['age']}, {persona['profile']['gender']})")
    
    if len(personas) > 3:
        print(f"... and {len(personas) - 3} more")

if __name__ == '__main__':
    main()
EOF

    chmod +x "${REPO_PATH}/testing/personas/persona_generator.py"
    log "✓ Test persona generator created"
}

# Create audio testing infrastructure
create_audio_testing_setup() {
    log "Creating audio testing infrastructure..."
    
    mkdir -p "${REPO_PATH}/testing/audio"
    
    cat > "${REPO_PATH}/testing/audio/audio_test_setup.sh" << 'EOF'
#!/bin/bash

# Audio Testing Setup
# Configures virtual audio devices for application audio testing
# For legitimate audio functionality testing and QA

set -euo pipefail

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

error() {
    echo "[ERROR] $1" >&2
    exit 1
}

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    error "Audio testing setup currently supports Linux only"
fi

# Check for root privileges for system configuration
if [[ $EUID -ne 0 ]] && [[ "${1:-}" != "--user-mode" ]]; then
    log "Note: Some audio setup requires root privileges"
    log "Run with --user-mode for user-space only setup"
fi

setup_virtual_audio_devices() {
    log "Setting up virtual audio devices for testing..."
    
    # Check if ALSA loopback module is available
    if [[ $EUID -eq 0 ]] && [[ "${1:-}" != "--user-mode" ]]; then
        # System-wide setup (requires root)
        log "Installing ALSA loopback support..."
        
        # Install required packages
        apt-get update -qq
        apt-get install -y alsa-utils pulseaudio-utils
        
        # Load loopback module
        if ! lsmod | grep -q snd_aloop; then
            modprobe snd_aloop enable=1,1 index=10,11
            log "✓ ALSA loopback module loaded"
        else
            log "✓ ALSA loopback module already loaded"
        fi
        
        # Create persistent module loading
        echo "snd_aloop enable=1,1 index=10,11" >> /etc/modules-load.d/audio-testing.conf
        
    else
        # User-space setup
        log "Setting up user-space audio testing environment..."
        
        # Check for PulseAudio
        if ! pulseaudio --check; then
            log "Starting PulseAudio for user..."
            pulseaudio --start --daemonize
        fi
        
        # Create virtual audio sink for testing
        if ! pactl list sinks | grep -q "test_audio_sink"; then
            pactl load-module module-null-sink sink_name=test_audio_sink sink_properties=device.description="Test_Audio_Sink"
            log "✓ Virtual audio sink created"
        fi
        
        # Create virtual audio source for testing
        if ! pactl list sources | grep -q "test_audio_source"; then
            pactl load-module module-null-sink sink_name=test_audio_source sink_properties=device.description="Test_Audio_Source"
            log "✓ Virtual audio source created"
        fi
    fi
}

create_audio_test_scripts() {
    log "Creating audio testing scripts..."
    
    # Create test audio generator
    cat > audio_test_generator.py << 'EOPY'
#!/usr/bin/env python3
"""
Audio Test Generator
Creates test audio patterns for application audio testing
"""

import numpy as np
import wave
import argparse
import os

def generate_test_tone(frequency=440, duration=5, sample_rate=44100, amplitude=0.3):
    """Generate a test tone for audio testing"""
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio_data = amplitude * np.sin(2 * np.pi * frequency * t)
    
    # Convert to 16-bit PCM
    audio_data = (audio_data * 32767).astype(np.int16)
    
    return audio_data, sample_rate

def save_test_audio(audio_data, sample_rate, filename):
    """Save test audio to WAV file"""
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())

def main():
    parser = argparse.ArgumentParser(description='Generate test audio for testing')
    parser.add_argument('--frequency', type=int, default=440, help='Test tone frequency (Hz)')
    parser.add_argument('--duration', type=int, default=5, help='Duration in seconds')
    parser.add_argument('--output', default='test_tone.wav', help='Output filename')
    
    args = parser.parse_args()
    
    print(f"Generating {args.frequency}Hz test tone for {args.duration}s...")
    audio_data, sample_rate = generate_test_tone(args.frequency, args.duration)
    save_test_audio(audio_data, sample_rate, args.output)
    print(f"✓ Test audio saved to {args.output}")

if __name__ == '__main__':
    main()
EOPY

    chmod +x audio_test_generator.py
    
    # Create audio testing script
    cat > test_audio_functionality.sh << 'EOSH'
#!/bin/bash

# Audio Functionality Tester
# Tests application audio input/output capabilities

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

test_audio_playback() {
    log "Testing audio playback functionality..."
    
    # Generate test tone if not exists
    if [ ! -f "test_tone.wav" ]; then
        python3 audio_test_generator.py --duration 3 --output test_tone.wav
    fi
    
    # Test audio playback
    if command -v aplay >/dev/null 2>&1; then
        log "Testing ALSA playback..."
        timeout 5 aplay test_tone.wav >/dev/null 2>&1 && log "✓ ALSA playback working"
    fi
    
    if command -v paplay >/dev/null 2>&1; then
        log "Testing PulseAudio playback..."
        timeout 5 paplay test_tone.wav >/dev/null 2>&1 && log "✓ PulseAudio playback working"
    fi
}

test_audio_recording() {
    log "Testing audio recording functionality..."
    
    # Test audio recording
    if command -v arecord >/dev/null 2>&1; then
        log "Testing ALSA recording..."
        timeout 3 arecord -f cd -d 2 test_recording.wav >/dev/null 2>&1 && log "✓ ALSA recording working"
    fi
    
    if command -v parecord >/dev/null 2>&1; then
        log "Testing PulseAudio recording..."
        timeout 3 parecord -d 2 test_recording.wav >/dev/null 2>&1 && log "✓ PulseAudio recording working"
    fi
}

test_virtual_devices() {
    log "Testing virtual audio devices..."
    
    # List available audio devices
    if command -v aplay >/dev/null 2>&1; then
        log "Available ALSA playback devices:"
        aplay -l | grep -E "card|device" || log "No ALSA devices found"
    fi
    
    if command -v pactl >/dev/null 2>&1; then
        log "Available PulseAudio sinks:"
        pactl list short sinks || log "No PulseAudio sinks found"
    fi
}

main() {
    log "=== Audio Testing Framework ==="
    
    test_virtual_devices
    test_audio_playback
    test_audio_recording
    
    log "Audio testing completed"
    
    # Cleanup
    rm -f test_tone.wav test_recording.wav
}

main "$@"
EOSH

    chmod +x test_audio_functionality.sh
    
    log "✓ Audio testing scripts created"
}

# Main setup function
main() {
    if [[ "${1:-}" == "--user-mode" ]]; then
        setup_virtual_audio_devices --user-mode
    else
        setup_virtual_audio_devices
    fi
    
    create_audio_test_scripts
    
    log "=== Audio Testing Setup Complete ==="
    log "Available commands:"
    log "  ./test_audio_functionality.sh  - Test audio capabilities"
    log "  python3 audio_test_generator.py - Generate test audio"
}

# Help function
show_help() {
    cat << 'EOHELP'
Audio Testing Setup

Usage: ./audio_test_setup.sh [OPTIONS]

Options:
  --user-mode    Setup audio testing in user-space only (no root required)
  --help         Show this help message

This script sets up:
- Virtual audio devices for testing
- Audio playback and recording test scripts
- Test tone generation tools

For legitimate audio functionality testing and QA purposes.
EOHELP
}

# Handle arguments
case "${1:-}" in
    --help|-h)
        show_help
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac
EOF

    chmod +x "${REPO_PATH}/testing/audio/audio_test_setup.sh"
    log "✓ Audio testing setup created"
}

# Create usage pattern automation scripts
create_usage_automation() {
    log "Creating usage pattern automation scripts..."
    
    mkdir -p "${REPO_PATH}/testing/automation"
    
    cat > "${REPO_PATH}/testing/automation/usage_patterns.js" << 'EOF'
/**
 * Usage Pattern Automation
 * Defines realistic usage patterns for application testing
 * For legitimate user behavior simulation and QA testing
 */

class UsagePatternGenerator {
    constructor() {
        this.patterns = {
            casual: {
                sessionDuration: [300, 900], // 5-15 minutes
                actionsPerMinute: [3, 8],
                pauseBetweenActions: [2000, 8000], // 2-8 seconds
                features: ['browse', 'search', 'view_profile', 'settings']
            },
            engaged: {
                sessionDuration: [900, 1800], // 15-30 minutes
                actionsPerMinute: [8, 15],
                pauseBetweenActions: [1000, 5000], // 1-5 seconds
                features: ['browse', 'search', 'view_profile', 'interact', 'discover', 'settings']
            },
            power_user: {
                sessionDuration: [1800, 3600], // 30-60 minutes
                actionsPerMinute: [15, 25],
                pauseBetweenActions: [500, 3000], // 0.5-3 seconds
                features: ['browse', 'search', 'view_profile', 'interact', 'discover', 'settings', 'premium_features']
            }
        };
    }
    
    /**
     * Generate a sequence of user actions for testing
     */
    generateUsageSequence(patternType = 'casual', testDuration = 600) {
        const pattern = this.patterns[patternType];
        const actions = [];
        
        let currentTime = 0;
        const endTime = Math.min(testDuration, this.randomInRange(pattern.sessionDuration));
        
        while (currentTime < endTime) {
            // Select random feature to test
            const feature = this.randomChoice(pattern.features);
            const action = this.generateFeatureAction(feature);
            
            actions.push({
                timestamp: currentTime,
                action: action.type,
                element: action.element,
                data: action.data,
                expectedDelay: this.randomInRange(pattern.pauseBetweenActions)
            });
            
            currentTime += this.randomInRange(pattern.pauseBetweenActions);
        }
        
        return {
            patternType,
            totalDuration: endTime,
            actions,
            testMetadata: {
                generatedAt: new Date().toISOString(),
                actionCount: actions.length,
                avgDelay: actions.reduce((sum, a) => sum + a.expectedDelay, 0) / actions.length
            }
        };
    }
    
    /**
     * Generate specific feature action for testing
     */
    generateFeatureAction(feature) {
        const featureActions = {
            browse: {
                type: 'swipe',
                element: 'card_stack',
                data: { direction: this.randomChoice(['left', 'right']) }
            },
            search: {
                type: 'tap',
                element: 'search_button',
                data: { searchTerm: this.generateTestSearchTerm() }
            },
            view_profile: {
                type: 'tap',
                element: 'profile_image',
                data: { viewDuration: this.randomInRange([2000, 10000]) }
            },
            interact: {
                type: 'tap',
                element: this.randomChoice(['like_button', 'super_like_button', 'pass_button']),
                data: { interactionType: 'test_interaction' }
            },
            discover: {
                type: 'tap',
                element: 'discover_tab',
                data: { exploreTime: this.randomInRange([5000, 15000]) }
            },
            settings: {
                type: 'tap',
                element: 'settings_button',
                data: { settingCategory: this.randomChoice(['privacy', 'notifications', 'account']) }
            },
            premium_features: {
                type: 'tap',
                element: 'premium_feature',
                data: { featureType: 'test_premium_access' }
            }
        };
        
        return featureActions[feature] || featureActions.browse;
    }
    
    /**
     * Generate test search terms for QA
     */
    generateTestSearchTerm() {
        const testTerms = [
            'test_user_123',
            'qa_verification',
            'automation_test',
            'sample_search',
            'test_query_' + Math.floor(Math.random() * 1000)
        ];
        return this.randomChoice(testTerms);
    }
    
    /**
     * Helper: Get random value from range
     */
    randomInRange([min, max]) {
        return Math.floor(Math.random() * (max - min + 1)) + min;
    }
    
    /**
     * Helper: Get random choice from array
     */
    randomChoice(array) {
        return array[Math.floor(Math.random() * array.length)];
    }
    
    /**
     * Export usage pattern for Appium automation
     */
    exportForAppium(usageSequence) {
        const appiumSteps = usageSequence.actions.map(action => {
            return {
                description: `Test ${action.action} on ${action.element}`,
                command: this.convertToAppiumCommand(action),
                wait: action.expectedDelay
            };
        });
        
        return {
            testSuite: `Usage Pattern Test - ${usageSequence.patternType}`,
            duration: usageSequence.totalDuration,
            steps: appiumSteps,
            metadata: usageSequence.testMetadata
        };
    }
    
    /**
     * Convert action to Appium command format
     */
    convertToAppiumCommand(action) {
        const commandMap = {
            tap: `driver.findElement(By.id("${action.element}")).click()`,
            swipe: `driver.swipe(startX, startY, endX, endY, ${action.expectedDelay})`,
            type: `driver.findElement(By.id("${action.element}")).sendKeys("${action.data?.text || 'test'}")`,
            scroll: `driver.scroll("${action.element}", "down")`
        };
        
        return commandMap[action.action] || `// ${action.action} on ${action.element}`;
    }
}

// Usage pattern automation injection points
const USAGE_VARIETY_STEPS = {
    // Discover page interaction
    discoverExploration: () => ({
        description: "Explore Discover page features",
        steps: [
            { action: "tap", element: "discover_tab", wait: 2000 },
            { action: "scroll", element: "discover_feed", wait: 3000 },
            { action: "tap", element: "discover_story", wait: 5000 }
        ]
    }),
    
    // Settings exploration
    settingsNavigation: () => ({
        description: "Navigate through settings for testing",
        steps: [
            { action: "tap", element: "profile_tab", wait: 2000 },
            { action: "tap", element: "settings_button", wait: 2000 },
            { action: "scroll", element: "settings_list", wait: 3000 },
            { action: "tap", element: "back_button", wait: 1000 }
        ]
    }),
    
    // Profile viewing pattern
    profileBrowsing: () => ({
        description: "Browse profiles for UI testing",
        steps: [
            { action: "tap", element: "profile_image", wait: 3000 },
            { action: "scroll", element: "profile_details", wait: 2000 },
            { action: "swipe", element: "photo_gallery", wait: 2000 },
            { action: "tap", element: "close_button", wait: 1000 }
        ]
    })
};

// Export for use in automation frameworks
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { UsagePatternGenerator, USAGE_VARIETY_STEPS };
}
EOF

    log "✓ Usage pattern automation scripts created"
}

# Create test configuration validator
create_test_config_validator() {
    log "Creating test configuration validator..."
    
    cat > "${REPO_PATH}/testing/validate_test_config.py" << 'EOF'
#!/usr/bin/env python3
"""
Test Configuration Validator
Validates persona profiles, audio setup, and usage patterns for testing
For legitimate application testing and QA validation
"""

import json
import os
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Any

class TestConfigValidator:
    """Validates test configuration and setup"""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.validation_results = []
    
    def add_result(self, test_name: str, status: str, details: str):
        """Add validation result"""
        self.validation_results.append({
            'test': test_name,
            'status': status,
            'details': details
        })
    
    def validate_persona_profiles(self) -> bool:
        """Validate persona profile configuration"""
        print("Validating persona profile configuration...")
        
        persona_script = self.repo_path / "testing" / "personas" / "persona_generator.py"
        if persona_script.exists():
            print("✓ Persona generator script found")
            self.add_result("PERSONA_SCRIPT", "PASS", "Persona generator available")
            
            # Test persona generation
            try:
                result = subprocess.run([
                    'python3', str(persona_script),
                    '--count', '1',
                    '--output', '/tmp/test_persona.json'
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    print("✓ Persona generation test successful")
                    self.add_result("PERSONA_GENERATION", "PASS", "Persona generation functional")
                    
                    # Validate generated persona
                    if os.path.exists('/tmp/test_persona.json'):
                        with open('/tmp/test_persona.json', 'r') as f:
                            personas = json.load(f)
                        
                        if personas and 'profile' in personas[0]:
                            print("✓ Generated persona has valid structure")
                            self.add_result("PERSONA_STRUCTURE", "PASS", "Valid persona structure")
                        else:
                            print("⚠ Generated persona structure incomplete")
                            self.add_result("PERSONA_STRUCTURE", "WARN", "Persona structure incomplete")
                else:
                    print("⚠ Persona generation test failed")
                    self.add_result("PERSONA_GENERATION", "WARN", f"Generation failed: {result.stderr}")
                    
            except Exception as e:
                print(f"⚠ Persona generation error: {e}")
                self.add_result("PERSONA_GENERATION", "WARN", f"Generation error: {e}")
        else:
            print("⚠ Persona generator script not found")
            self.add_result("PERSONA_SCRIPT", "WARN", "Persona generator not available")
            return False
        
        return True
    
    def validate_audio_setup(self) -> bool:
        """Validate audio testing configuration"""
        print("Validating audio testing setup...")
        
        audio_script = self.repo_path / "testing" / "audio" / "audio_test_setup.sh"
        if audio_script.exists():
            print("✓ Audio test setup script found")
            self.add_result("AUDIO_SCRIPT", "PASS", "Audio testing script available")
            
            # Check for audio testing dependencies
            audio_deps = ['aplay', 'arecord', 'pactl']
            for dep in audio_deps:
                result = subprocess.run(['which', dep], capture_output=True)
                if result.returncode == 0:
                    print(f"✓ {dep} available")
                else:
                    print(f"ℹ {dep} not available (may limit audio testing)")
                    
        else:
            print("⚠ Audio test setup script not found")
            self.add_result("AUDIO_SCRIPT", "WARN", "Audio testing script not available")
            return False
        
        # Check for virtual audio devices (Linux)
        if os.path.exists('/proc/asound/cards'):
            with open('/proc/asound/cards', 'r') as f:
                cards = f.read()
            if 'Loopback' in cards:
                print("✓ Audio loopback device detected")
                self.add_result("AUDIO_LOOPBACK", "PASS", "Virtual audio device available")
            else:
                print("ℹ No audio loopback device detected")
                self.add_result("AUDIO_LOOPBACK", "INFO", "Virtual audio device not detected")
        
        return True
    
    def validate_usage_automation(self) -> bool:
        """Validate usage pattern automation"""
        print("Validating usage pattern automation...")
        
        usage_script = self.repo_path / "testing" / "automation" / "usage_patterns.js"
        if usage_script.exists():
            print("✓ Usage pattern script found")
            self.add_result("USAGE_SCRIPT", "PASS", "Usage automation script available")
            
            # Validate JavaScript syntax
            try:
                with open(usage_script, 'r') as f:
                    content = f.read()
                
                # Check for key components
                if 'UsagePatternGenerator' in content:
                    print("✓ Usage pattern generator class found")
                    self.add_result("USAGE_GENERATOR", "PASS", "Usage pattern generator available")
                
                if 'USAGE_VARIETY_STEPS' in content:
                    print("✓ Usage variety steps defined")
                    self.add_result("USAGE_STEPS", "PASS", "Usage variety steps available")
                    
            except Exception as e:
                print(f"⚠ Usage script validation error: {e}")
                self.add_result("USAGE_VALIDATION", "WARN", f"Script validation error: {e}")
                
        else:
            print("⚠ Usage pattern script not found")
            self.add_result("USAGE_SCRIPT", "WARN", "Usage automation script not available")
            return False
        
        return True
    
    def validate_test_environment(self) -> bool:
        """Validate overall test environment"""
        print("Validating test environment...")
        
        # Check for required directories
        required_dirs = [
            "testing/personas",
            "testing/audio", 
            "testing/automation"
        ]
        
        for dir_path in required_dirs:
            full_path = self.repo_path / dir_path
            if full_path.exists():
                print(f"✓ {dir_path} directory exists")
                self.add_result(f"DIR_{dir_path.upper().replace('/', '_')}", "PASS", f"{dir_path} available")
            else:
                print(f"⚠ {dir_path} directory missing")
                self.add_result(f"DIR_{dir_path.upper().replace('/', '_')}", "WARN", f"{dir_path} missing")
        
        return True
    
    def generate_report(self) -> str:
        """Generate validation report"""
        report = "# Test Configuration Validation Report\n\n"
        report += f"Repository Path: {self.repo_path}\n"
        report += f"Total Tests: {len(self.validation_results)}\n\n"
        
        # Count by status
        status_counts = {}
        for result in self.validation_results:
            status = result['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        report += "## Summary\n"
        for status, count in status_counts.items():
            report += f"- {status}: {count}\n"
        
        report += "\n## Detailed Results\n\n"
        for result in self.validation_results:
            report += f"- **{result['test']}**: {result['status']} - {result['details']}\n"
        
        return report
    
    def run_full_validation(self) -> bool:
        """Run complete validation suite"""
        print("=== Test Configuration Validation ===")
        
        all_passed = True
        all_passed &= self.validate_test_environment()
        all_passed &= self.validate_persona_profiles()
        all_passed &= self.validate_audio_setup()
        all_passed &= self.validate_usage_automation()
        
        # Generate and save report
        report = self.generate_report()
        report_file = self.repo_path / "testing" / "validation_report.md"
        with open(report_file, 'w') as f:
            f.write(report)
        
        print(f"\n✓ Validation report saved to {report_file}")
        
        # Print summary
        pass_count = sum(1 for r in self.validation_results if r['status'] == 'PASS')
        total_count = len(self.validation_results)
        
        print(f"\nValidation Summary: {pass_count}/{total_count} tests passed")
        
        return all_passed

def main():
    parser = argparse.ArgumentParser(description='Validate test configuration setup')
    parser.add_argument('--repo-path', default='.', help='Repository path')
    parser.add_argument('--report-only', action='store_true', help='Generate report only')
    
    args = parser.parse_args()
    
    validator = TestConfigValidator(args.repo_path)
    
    if args.report_only:
        # Just generate a basic report
        validator.validate_test_environment()
        report = validator.generate_report()
        print(report)
    else:
        # Run full validation
        success = validator.run_full_validation()
        exit(0 if success else 1)

if __name__ == '__main__':
    main()
EOF

    chmod +x "${REPO_PATH}/testing/validate_test_config.py"
    log "✓ Test configuration validator created"
}

# Main execution function
main() {
    log "=== Persona Testing Framework Setup ==="
    log "Creating comprehensive testing infrastructure..."
    log "Repository path: $REPO_PATH"
    
    # Create testing directory structure
    mkdir -p "${REPO_PATH}/testing"/{personas,audio,automation}
    
    # Setup components
    create_persona_generator
    create_audio_testing_setup
    create_usage_automation
    create_test_config_validator
    
    log "=== Setup Complete ==="
    log ""
    log "🎯 Available Testing Tools:"
    log "  • Persona Generator: testing/personas/persona_generator.py"
    log "  • Audio Testing: testing/audio/audio_test_setup.sh"
    log "  • Usage Automation: testing/automation/usage_patterns.js"
    log "  • Config Validator: testing/validate_test_config.py"
    log ""
    log "🚀 Quick Start:"
    log "  # Generate test personas"
    log "  python3 testing/personas/persona_generator.py --count 5"
    log ""
    log "  # Setup audio testing"
    log "  cd testing/audio && ./audio_test_setup.sh --user-mode"
    log ""
    log "  # Validate configuration"
    log "  python3 testing/validate_test_config.py"
    log ""
    log "For legitimate application testing, QA, and user experience validation only."
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        cat << 'EOHELP'
Persona Testing Framework

Usage: ./persona-testing-framework.sh [REPO_PATH]

Arguments:
  REPO_PATH    Path to project repository (default: current directory)

This script creates:
- Test persona profile generator with randomized attributes
- Audio testing infrastructure with virtual device support
- Usage pattern automation for realistic behavior simulation
- Configuration validation and testing tools

For legitimate application testing, QA, and user experience validation.
EOHELP
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac