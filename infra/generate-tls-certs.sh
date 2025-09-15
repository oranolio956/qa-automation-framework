#!/bin/bash
# TLS Certificate Generation Script for Development/Testing
# WARNING: These are self-signed certificates for development only
# Use proper CA-signed certificates in production

set -e

# Configuration
CERT_DIR="./config/tls"
VALIDITY_DAYS=365
COUNTRY="US"
STATE="Colorado"
CITY="Denver"
ORG="Automation Infrastructure"
OU="Development"

# Create certificate directory
mkdir -p "$CERT_DIR"
cd "$CERT_DIR"

echo "🔐 Generating TLS certificates for development/testing..."

# Generate CA private key
echo "📝 Generating CA private key..."
openssl genrsa -out ca.key 4096

# Generate CA certificate
echo "📝 Generating CA certificate..."
openssl req -new -x509 -days $VALIDITY_DAYS -key ca.key -out ca.crt -subj "/C=$COUNTRY/ST=$STATE/L=$CITY/O=$ORG/OU=$OU/CN=Development CA"

# Generate server private key
echo "📝 Generating server private key..."
openssl genrsa -out server.key 2048

# Generate server certificate signing request
echo "📝 Generating server CSR..."
openssl req -new -key server.key -out server.csr -subj "/C=$COUNTRY/ST=$STATE/L=$CITY/O=$ORG/OU=$OU/CN=localhost"

# Create server certificate extensions file
cat > server.ext << EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = redis
DNS.3 = rabbitmq
DNS.4 = vault
DNS.5 = *.infra_network
IP.1 = 127.0.0.1
IP.2 = 0.0.0.0
EOF

# Generate server certificate signed by CA
echo "📝 Generating server certificate..."
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days $VALIDITY_DAYS -extensions v3_req -extfile server.ext

# Create Redis-specific certificates (Redis expects specific names)
cp server.crt redis.crt
cp server.key redis.key

# Create Vault-specific certificates
cp server.crt vault.crt
cp server.key vault.key

# Generate client certificates for mutual TLS
echo "📝 Generating client certificate..."
openssl genrsa -out client.key 2048
openssl req -new -key client.key -out client.csr -subj "/C=$COUNTRY/ST=$STATE/L=$CITY/O=$ORG/OU=$OU/CN=client"
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out client.crt -days $VALIDITY_DAYS

# Set appropriate permissions
chmod 600 *.key
chmod 644 *.crt

# Clean up temporary files
rm -f *.csr *.ext *.srl

echo "✅ TLS certificates generated successfully!"
echo "📁 Certificates location: $PWD"
echo ""
echo "📋 Generated files:"
echo "   ca.crt          - Certificate Authority"
echo "   ca.key          - CA private key"
echo "   server.crt      - Server certificate"
echo "   server.key      - Server private key"
echo "   redis.crt       - Redis-specific certificate"
echo "   redis.key       - Redis-specific private key"
echo "   vault.crt       - Vault-specific certificate"
echo "   vault.key       - Vault-specific private key"
echo "   client.crt      - Client certificate (for mutual TLS)"
echo "   client.key      - Client private key"
echo ""
echo "⚠️  SECURITY WARNING:"
echo "   These are self-signed certificates for DEVELOPMENT ONLY"
echo "   Use proper CA-signed certificates in production"
echo "   Keep private keys secure and never commit them to version control"
echo ""
echo "🚀 Next steps:"
echo "   1. Copy .env.production.template to .env"
echo "   2. Replace all REPLACE_WITH_* values with actual secrets"
echo "   3. Set VAULT_TLS_DISABLE=false in .env"
echo "   4. Run: docker-compose up -d"

# Display certificate information
echo ""
echo "📊 Certificate Information:"
echo "CA Certificate:"
openssl x509 -in ca.crt -noout -text | grep -A 2 "Subject:"
echo ""
echo "Server Certificate:"
openssl x509 -in server.crt -noout -text | grep -A 2 "Subject:"
openssl x509 -in server.crt -noout -text | grep -A 10 "Subject Alternative Name"