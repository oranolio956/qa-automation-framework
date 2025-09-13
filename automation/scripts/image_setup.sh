#!/bin/bash
# Image Setup and Generation Script for QA Testing
# Handles dynamic placeholder image generation and metadata variation

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_DIR="${TEST_DIR:-/tmp/qa-test-images}"
IMAGE_SERVICE_URL="${IMAGE_SERVICE_URL:-http://localhost:3001/api/generate}"

# Smartproxy configuration
SMARTPROXY_USER="${SMARTPROXY_USER:-your_trial_user}"
SMARTPROXY_PASS="${SMARTPROXY_PASS:-your_trial_pass}"
SMARTPROXY_HOST="${SMARTPROXY_HOST:-proxy.smartproxy.com}"
SMARTPROXY_PORT="${SMARTPROXY_PORT:-7000}"
PROXY_URL="socks5://${SMARTPROXY_USER}:${SMARTPROXY_PASS}@${SMARTPROXY_HOST}:${SMARTPROXY_PORT}"

# Proxy-enabled curl function
curl_proxy() {
    curl --proxy-user "${SMARTPROXY_USER}:${SMARTPROXY_PASS}" \
         --socks5-hostname "${SMARTPROXY_HOST}:${SMARTPROXY_PORT}" \
         "$@"
}

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

setup_test_directory() {
    log "Setting up test image directory: $TEST_DIR"
    mkdir -p "$TEST_DIR"
    chmod 755 "$TEST_DIR"
}

fetch_placeholder() {
    local size="${1:-1024}"
    local image_type="${2:-profile}"
    local output_file="$3"
    
    log "Fetching placeholder image (size: $size, type: $image_type)..."
    
    # Generate placeholder image via REST API
    local request_data="{\"size\":$size,\"type\":\"$image_type\",\"format\":\"jpg\"}"
    
    if command -v curl >/dev/null 2>&1; then
        # Try to fetch from image generation service through proxy
        if img_url=$(curl_proxy -s -X POST "$IMAGE_SERVICE_URL" \
            -H "Content-Type: application/json" \
            -d "$request_data" | jq -r '.url' 2>/dev/null); then
            
            if [ "$img_url" != "null" ] && [ -n "$img_url" ]; then
                curl_proxy -s "$img_url" -o "$output_file"
                log "Downloaded image from: $img_url through proxy"
                return 0
            fi
        fi
    fi
    
    # Fallback: Generate local placeholder
    log "Using local placeholder generation fallback"
    generate_local_placeholder "$size" "$output_file"
}

generate_local_placeholder() {
    local size="$1"
    local output_file="$2"
    
    # Generate a simple placeholder image using ImageMagick
    if command -v convert >/dev/null 2>&1; then
        convert -size "${size}x${size}" \
            -background "#$(printf '%06x' $((RANDOM * RANDOM % 16777216)))" \
            -fill white \
            -gravity center \
            -pointsize $((size / 20)) \
            -annotate +0+0 "QA Test\n${size}x${size}" \
            "$output_file"
    else
        # Ultra-simple fallback: create a minimal test file
        echo "QA Test Image Placeholder" > "$output_file"
    fi
}

apply_metadata_variations() {
    local input_file="$1"
    local output_file="$2"
    
    log "Applying metadata variations to $(basename "$input_file")..."
    
    if [ ! -f "$input_file" ]; then
        log "Warning: Input file $input_file not found"
        return 1
    fi
    
    if command -v convert >/dev/null 2>&1; then
        # Apply random variations using ImageMagick
        local brightness=$((RANDOM % 20 - 10))  # -10 to +10
        local contrast=$((RANDOM % 20 - 10))    # -10 to +10
        local rotation=$((RANDOM % 6 - 3))      # -3 to +3 degrees
        
        convert "$input_file" \
            -strip \
            -set DateTimeOriginal "$(date +%Y:%m:%d\ %H:%M:%S)" \
            -brightness-contrast "${brightness}x${contrast}" \
            -rotate "$rotation" \
            -quality $((80 + RANDOM % 20)) \
            "$output_file"
        
        log "Applied variations: brightness=$brightness, contrast=$contrast, rotation=$rotation"
    else
        # Fallback: just copy the file
        cp "$input_file" "$output_file"
    fi
}

generate_test_image_set() {
    local count="${1:-10}"
    local base_name="${2:-test_image}"
    
    log "Generating $count test images..."
    
    for i in $(seq 1 "$count"); do
        local size=$((512 + RANDOM % 512))  # Random size between 512-1024
        local base_file="$TEST_DIR/${base_name}_${i}_base.jpg"
        local var_file="$TEST_DIR/${base_name}_${i}_var.jpg"
        
        # Fetch base placeholder image
        fetch_placeholder "$size" "profile" "$base_file"
        
        # Apply metadata variations
        apply_metadata_variations "$base_file" "$var_file"
        
        log "Generated test image set $i/$count"
    done
}

create_image_categories() {
    log "Creating categorized test images..."
    
    local categories=("profile" "landscape" "portrait" "object" "text")
    
    for category in "${categories[@]}"; do
        local cat_dir="$TEST_DIR/$category"
        mkdir -p "$cat_dir"
        
        for i in {1..5}; do
            local base_file="$cat_dir/${category}_${i}.jpg"
            fetch_placeholder 800 "$category" "$base_file"
            
            # Create a variation
            local var_file="$cat_dir/${category}_${i}_variant.jpg"
            apply_metadata_variations "$base_file" "$var_file"
        done
        
        log "Created $category category images"
    done
}

cleanup_old_images() {
    local max_age_days="${1:-7}"
    
    log "Cleaning up images older than $max_age_days days..."
    
    if [ -d "$TEST_DIR" ]; then
        find "$TEST_DIR" -name "*.jpg" -mtime "+$max_age_days" -delete
        find "$TEST_DIR" -name "*.png" -mtime "+$max_age_days" -delete
    fi
}

verify_images() {
    log "Verifying generated images..."
    
    local total_images=0
    local valid_images=0
    
    if [ -d "$TEST_DIR" ]; then
        while IFS= read -r -d '' file; do
            ((total_images++))
            if file "$file" | grep -q "image"; then
                ((valid_images++))
            fi
        done < <(find "$TEST_DIR" -name "*.jpg" -print0)
    fi
    
    log "Image verification: $valid_images/$total_images valid images"
    
    if [ "$valid_images" -eq 0 ]; then
        log "Warning: No valid images found!"
        return 1
    fi
    
    return 0
}

main() {
    log "Starting image setup for QA testing..."
    
    # Setup
    setup_test_directory
    
    # Generate test images
    generate_test_image_set 20
    create_image_categories
    
    # Cleanup old files
    cleanup_old_images 7
    
    # Verify
    verify_images
    
    log "Image setup completed successfully"
    log "Test images available in: $TEST_DIR"
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi