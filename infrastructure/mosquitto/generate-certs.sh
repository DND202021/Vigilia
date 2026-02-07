#!/bin/bash
#
# Vigilia MQTT Broker - TLS Certificate Generation
#
# Generates self-signed CA and certificates for:
# - CA (Certificate Authority)
# - Server certificate (for Mosquitto broker)
# - Internal client certificate (for FastAPI backend)
#
# Usage:
#   ./generate-certs.sh        # Generate only if missing
#   ./generate-certs.sh --force # Regenerate all certificates

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERTS_DIR="$SCRIPT_DIR/certs"

FORCE=false
if [[ "$1" == "--force" ]]; then
    FORCE=true
fi

# Check if certificates already exist
if [[ -f "$CERTS_DIR/ca.crt" ]] && [[ -f "$CERTS_DIR/server.crt" ]] && [[ -f "$CERTS_DIR/internal-client.crt" ]] && [[ "$FORCE" != true ]]; then
    echo "Certificates already exist. Use --force to regenerate."
    exit 0
fi

echo "Generating TLS certificates for Vigilia MQTT Broker..."
mkdir -p "$CERTS_DIR"
cd "$CERTS_DIR"

# Clean up old certificates if forcing regeneration
if [[ "$FORCE" == true ]]; then
    echo "Removing old certificates..."
    rm -f *.key *.crt *.csr *.pem
fi

# 1. Generate CA (Certificate Authority)
echo "Generating CA certificate..."
openssl genrsa -out ca.key 4096
openssl req -new -x509 -days 3650 -key ca.key -out ca.crt \
    -subj "/C=US/ST=California/L=San Francisco/O=Vigilia/OU=IoT/CN=Vigilia MQTT CA"

# 2. Generate Server Certificate (for Mosquitto broker)
echo "Generating server certificate..."
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr \
    -subj "/C=US/ST=California/L=San Francisco/O=Vigilia/OU=IoT/CN=mosquitto"

# Create server certificate extensions file (with SAN)
cat > server_ext.cnf <<EOF
basicConstraints = CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = mosquitto
DNS.2 = localhost
IP.1 = 127.0.0.1
EOF

openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out server.crt -days 3650 -extfile server_ext.cnf

# 3. Generate Internal Client Certificate (for FastAPI backend)
echo "Generating internal client certificate..."
openssl genrsa -out internal-client.key 2048
openssl req -new -key internal-client.key -out internal-client.csr \
    -subj "/C=US/ST=California/L=San Francisco/O=Vigilia/OU=Backend/CN=vigilia-backend"

# Create client certificate extensions file
cat > client_ext.cnf <<EOF
basicConstraints = CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = clientAuth
EOF

openssl x509 -req -in internal-client.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out internal-client.crt -days 3650 -extfile client_ext.cnf

# Clean up temporary files
rm -f *.csr *.cnf *.srl

# Set proper permissions
chmod 600 *.key
chmod 644 *.crt

echo "Certificate generation complete!"
echo "  CA: ca.crt (ca.key)"
echo "  Server: server.crt (server.key)"
echo "  Client: internal-client.crt (internal-client.key)"
echo ""
echo "To view certificate details:"
echo "  openssl x509 -in server.crt -text -noout"
