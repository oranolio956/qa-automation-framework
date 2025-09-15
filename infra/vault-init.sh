#!/bin/bash
# Vault Initialization Script for Secure Credential Management
# This script sets up Vault with all required secrets for production deployment

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔐 INITIALIZING HASHICORP VAULT FOR SECURE CREDENTIALS${NC}"
echo "================================================================="

# Check if Vault is running
if ! curl -s http://localhost:8200/v1/sys/health >/dev/null 2>&1; then
    echo -e "${RED}❌ Vault is not running. Start Vault first with: docker-compose up -d vault${NC}"
    exit 1
fi

# Check if Vault is initialized
if curl -s http://localhost:8200/v1/sys/init | jq -r .initialized 2>/dev/null | grep -q "true"; then
    echo -e "${YELLOW}⚠️ Vault is already initialized. Using existing setup.${NC}"
    VAULT_INITIALIZED=true
else
    echo -e "${GREEN}✅ Initializing new Vault instance...${NC}"
    VAULT_INITIALIZED=false
fi

# Initialize Vault if needed
if [ "$VAULT_INITIALIZED" = false ]; then
    echo "🔧 Initializing Vault with 5 key shares and threshold of 3..."
    VAULT_INIT=$(curl -s -X PUT -d '{"secret_shares": 5, "secret_threshold": 3}' http://localhost:8200/v1/sys/init)
    
    # Extract keys and root token
    VAULT_ROOT_TOKEN=$(echo "$VAULT_INIT" | jq -r .root_token)
    UNSEAL_KEY_1=$(echo "$VAULT_INIT" | jq -r .keys[0])
    UNSEAL_KEY_2=$(echo "$VAULT_INIT" | jq -r .keys[1])
    UNSEAL_KEY_3=$(echo "$VAULT_INIT" | jq -r .keys[2])
    
    echo -e "${GREEN}✅ Vault initialized successfully${NC}"
    
    # Unseal Vault
    echo "🔓 Unsealing Vault..."
    curl -s -X PUT -d "{\"key\": \"$UNSEAL_KEY_1\"}" http://localhost:8200/v1/sys/unseal >/dev/null
    curl -s -X PUT -d "{\"key\": \"$UNSEAL_KEY_2\"}" http://localhost:8200/v1/sys/unseal >/dev/null
    curl -s -X PUT -d "{\"key\": \"$UNSEAL_KEY_3\"}" http://localhost:8200/v1/sys/unseal >/dev/null
    
    echo -e "${GREEN}✅ Vault unsealed and ready${NC}"
    
    # Save credentials securely (for this demo - in production use proper key management)
    mkdir -p ./secrets/vault
    echo "$VAULT_ROOT_TOKEN" > ./secrets/vault/root-token
    echo "$UNSEAL_KEY_1" > ./secrets/vault/unseal-key-1
    echo "$UNSEAL_KEY_2" > ./secrets/vault/unseal-key-2
    echo "$UNSEAL_KEY_3" > ./secrets/vault/unseal-key-3
    chmod 600 ./secrets/vault/*
    
    echo -e "${YELLOW}⚠️ Vault keys saved to ./secrets/vault/ - KEEP THESE SECURE!${NC}"
else
    # Load existing root token
    if [ -f "./secrets/vault/root-token" ]; then
        VAULT_ROOT_TOKEN=$(cat ./secrets/vault/root-token)
        echo -e "${GREEN}✅ Using existing Vault root token${NC}"
    else
        echo -e "${RED}❌ Vault is initialized but no root token found. Please provide manually.${NC}"
        read -s -p "Enter Vault root token: " VAULT_ROOT_TOKEN
        echo
    fi
fi

export VAULT_TOKEN="$VAULT_ROOT_TOKEN"
export VAULT_ADDR="http://localhost:8200"

echo
echo -e "${BLUE}🔧 SETTING UP SECRET ENGINES AND POLICIES${NC}"
echo "=========================================="

# Enable KV secrets engine v2
echo "📁 Enabling KV secrets engine..."
curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" -d '{"type": "kv", "options": {"version": "2"}}' \
    http://localhost:8200/v1/sys/mounts/secret >/dev/null 2>&1 || echo "KV engine already enabled"

echo -e "${GREEN}✅ KV secrets engine enabled${NC}"

# Create policies for different services
echo "📋 Creating service policies..."

# SMS Service policy
curl -s -X PUT -H "X-Vault-Token: $VAULT_TOKEN" -d '{
    "policy": "path \"secret/data/twilio\" { capabilities = [\"read\"] }\npath \"secret/data/aws/sns\" { capabilities = [\"read\"] }"
}' http://localhost:8200/v1/sys/policies/acl/sms-service >/dev/null

# Email Service policy
curl -s -X PUT -H "X-Vault-Token: $VAULT_TOKEN" -d '{
    "policy": "path \"secret/data/rapidapi\" { capabilities = [\"read\"] }\npath \"secret/data/captcha\" { capabilities = [\"read\"] }"
}' http://localhost:8200/v1/sys/policies/acl/email-service >/dev/null

# Database policy
curl -s -X PUT -H "X-Vault-Token: $VAULT_TOKEN" -d '{
    "policy": "path \"secret/data/database\" { capabilities = [\"read\"] }\npath \"secret/data/redis\" { capabilities = [\"read\"] }"
}' http://localhost:8200/v1/sys/policies/acl/database-service >/dev/null

echo -e "${GREEN}✅ Service policies created${NC}"

echo
echo -e "${BLUE}🔑 STORING PRODUCTION SECRETS${NC}"
echo "============================="

# Function to prompt for secrets
prompt_secret() {
    local name=$1
    local description=$2
    local default_value=${3:-""}
    
    if [ -n "$default_value" ]; then
        read -p "Enter $description [$default_value]: " value
        value=${value:-$default_value}
    else
        read -s -p "Enter $description (hidden): " value
        echo
    fi
    
    if [ -z "$value" ]; then
        echo -e "${YELLOW}⚠️ Skipping empty value for $name${NC}"
        return 1
    fi
    
    echo "$value"
}

# Twilio credentials
echo "📱 Twilio SMS Service credentials:"
if TWILIO_SID=$(prompt_secret "twilio_account_sid" "Twilio Account SID"); then
    if TWILIO_TOKEN=$(prompt_secret "twilio_auth_token" "Twilio Auth Token"); then
        if TWILIO_PHONE=$(prompt_secret "twilio_phone" "Twilio Phone Number" "+15551234567"); then
            curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" -d "{
                \"data\": {
                    \"account_sid\": \"$TWILIO_SID\",
                    \"auth_token\": \"$TWILIO_TOKEN\",
                    \"phone_numbers\": [\"$TWILIO_PHONE\"]
                }
            }" http://localhost:8200/v1/secret/data/twilio >/dev/null
            echo -e "${GREEN}✅ Twilio credentials stored${NC}"
        fi
    fi
fi

# AWS credentials
echo
echo "☁️ AWS SNS Service credentials:"
if AWS_KEY=$(prompt_secret "aws_access_key" "AWS Access Key ID"); then
    if AWS_SECRET=$(prompt_secret "aws_secret_key" "AWS Secret Access Key"); then
        AWS_REGION=$(prompt_secret "aws_region" "AWS Region" "us-east-1")
        curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" -d "{
            \"data\": {
                \"access_key_id\": \"$AWS_KEY\",
                \"secret_access_key\": \"$AWS_SECRET\",
                \"region\": \"$AWS_REGION\",
                \"sns_topic_arn\": \"arn:aws:sns:$AWS_REGION:123456789012:sms-notifications\"
            }
        }" http://localhost:8200/v1/secret/data/aws/sns >/dev/null
        echo -e "${GREEN}✅ AWS credentials stored${NC}"
    fi
fi

# RapidAPI credentials
echo
echo "🔌 RapidAPI credentials:"
if RAPIDAPI_KEY=$(prompt_secret "rapidapi_key" "RapidAPI Key"); then
    curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" -d "{
        \"data\": {
            \"api_key\": \"$RAPIDAPI_KEY\",
            \"endpoints\": [\"email-service\", \"temp-email\", \"verification\"]
        }
    }" http://localhost:8200/v1/secret/data/rapidapi >/dev/null
    echo -e "${GREEN}✅ RapidAPI credentials stored${NC}"
fi

# CAPTCHA services
echo
echo "🤖 CAPTCHA solving service credentials:"
if CAPTCHA_2CAPTCHA=$(prompt_secret "2captcha_key" "2Captcha API Key (optional)" ""); then
    if CAPTCHA_ANTI=$(prompt_secret "anticaptcha_key" "AntiCaptcha API Key (optional)" ""); then
        CAPTCHA_CAPMONSTER=$(prompt_secret "capmonster_key" "CapMonster API Key (optional)" "")
        curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" -d "{
            \"data\": {
                \"twocaptcha_key\": \"$CAPTCHA_2CAPTCHA\",
                \"anticaptcha_key\": \"$CAPTCHA_ANTI\",
                \"capmonster_key\": \"$CAPTCHA_CAPMONSTER\"
            }
        }" http://localhost:8200/v1/secret/data/captcha >/dev/null
        echo -e "${GREEN}✅ CAPTCHA service credentials stored${NC}"
    fi
fi

# Database credentials
echo
echo "🗄️ Database credentials:"
# Generate secure Redis password
REDIS_PASSWORD=$(openssl rand -base64 32)
DB_CONNECTION="postgresql://tinder_user:$(openssl rand -base64 16)@postgres:5432/tinder_bot"

curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" -d "{
    \"data\": {
        \"connection_string\": \"$DB_CONNECTION\",
        \"redis_password\": \"$REDIS_PASSWORD\"
    }
}" http://localhost:8200/v1/secret/data/database >/dev/null

curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" -d "{
    \"data\": {
        \"password\": \"$REDIS_PASSWORD\"
    }
}" http://localhost:8200/v1/secret/data/redis >/dev/null

echo -e "${GREEN}✅ Database credentials generated and stored${NC}"

# Proxy credentials (optional)
echo
echo "🌐 Proxy service credentials (optional):"
if PROXY_USER=$(prompt_secret "proxy_user" "Proxy username (optional)" ""); then
    PROXY_PASS=$(prompt_secret "proxy_pass" "Proxy password")
    PROXY_URL=$(prompt_secret "proxy_url" "Proxy URL" "http://proxy.example.com:8080")
    curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" -d "{
        \"data\": {
            \"username\": \"$PROXY_USER\",
            \"password\": \"$PROXY_PASS\",
            \"brightdata_url\": \"$PROXY_URL\"
        }
    }" http://localhost:8200/v1/secret/data/proxies >/dev/null
    echo -e "${GREEN}✅ Proxy credentials stored${NC}"
fi

echo
echo -e "${BLUE}🎫 CREATING SERVICE TOKENS${NC}"
echo "=========================="

# Create tokens for each service
SMS_TOKEN=$(curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" -d '{
    "policies": ["sms-service"],
    "ttl": "24h",
    "renewable": true
}' http://localhost:8200/v1/auth/token/create | jq -r .auth.client_token)

EMAIL_TOKEN=$(curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" -d '{
    "policies": ["email-service"],
    "ttl": "24h",
    "renewable": true
}' http://localhost:8200/v1/auth/token/create | jq -r .auth.client_token)

DB_TOKEN=$(curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" -d '{
    "policies": ["database-service"],
    "ttl": "24h",
    "renewable": true
}' http://localhost:8200/v1/auth/token/create | jq -r .auth.client_token)

# Save service tokens
mkdir -p ./secrets/vault/tokens
echo "$SMS_TOKEN" > ./secrets/vault/tokens/sms-service-token
echo "$EMAIL_TOKEN" > ./secrets/vault/tokens/email-service-token
echo "$DB_TOKEN" > ./secrets/vault/tokens/database-service-token
chmod 600 ./secrets/vault/tokens/*

echo -e "${GREEN}✅ Service tokens created and saved${NC}"

echo
echo -e "${BLUE}🧪 TESTING SECRET RETRIEVAL${NC}"
echo "========================="

# Test secret retrieval
echo "🔍 Testing Twilio secret retrieval..."
TWILIO_TEST=$(curl -s -H "X-Vault-Token: $SMS_TOKEN" http://localhost:8200/v1/secret/data/twilio | jq -r .data.data.account_sid 2>/dev/null)
if [ "$TWILIO_TEST" != "null" ] && [ -n "$TWILIO_TEST" ]; then
    echo -e "${GREEN}✅ Twilio secrets accessible with service token${NC}"
else
    echo -e "${YELLOW}⚠️ Twilio secrets test failed (may be empty)${NC}"
fi

echo "🔍 Testing database secret retrieval..."
REDIS_TEST=$(curl -s -H "X-Vault-Token: $DB_TOKEN" http://localhost:8200/v1/secret/data/redis | jq -r .data.data.password 2>/dev/null)
if [ "$REDIS_TEST" != "null" ] && [ -n "$REDIS_TEST" ]; then
    echo -e "${GREEN}✅ Database secrets accessible with service token${NC}"
else
    echo -e "${YELLOW}⚠️ Database secrets test failed${NC}"
fi

echo
echo -e "${GREEN}🎉 VAULT SETUP COMPLETE!${NC}"
echo "======================="
echo
echo -e "${BLUE}📋 NEXT STEPS:${NC}"
echo "1. Update .env file with generated passwords:"
echo "   REDIS_PASSWORD=$(cat ./secrets/vault/tokens/database-service-token | head -c 20)"
echo
echo "2. Mount Vault tokens in Docker containers:"
echo "   - SMS Service: /vault/secrets/sms-service-token"
echo "   - Email Service: /vault/secrets/email-service-token" 
echo "   - Database Service: /vault/secrets/database-service-token"
echo
echo "3. Services will automatically retrieve credentials from Vault at runtime"
echo
echo "4. Start all services:"
echo "   docker-compose --env-file .env up -d"
echo
echo -e "${YELLOW}⚠️ SECURITY REMINDERS:${NC}"
echo "• Keep ./secrets/ directory secure and never commit to git"
echo "• Rotate service tokens regularly (they expire in 24h)"
echo "• Monitor Vault audit logs for unauthorized access"
echo "• Use Vault's auto-unseal feature in production"
echo
echo -e "${BLUE}🔐 Vault is ready for secure credential management!${NC}"