#!/bin/bash
# Startup script for UltraDL YouTube Downloader VM
# This script runs when the Compute Engine instance starts

set -e

# Update system packages
apt-get update
apt-get upgrade -y

# Install Docker
apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Start and enable Docker
systemctl start docker
systemctl enable docker

# Install Docker Compose (standalone)
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Create application directory
mkdir -p /opt/ultradl
cd /opt/ultradl

# Get GCS bucket name from instance metadata
GCS_BUCKET=$(curl -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/attributes/gcs-bucket-name)

# Create environment file
cat > .env <<EOF
GCS_BUCKET_NAME=${GCS_BUCKET}
REDIS_URL=redis://redis:6379
FLASK_ENV=production
EOF

# Log completion
echo "Startup script completed successfully" | tee /var/log/startup-script.log
echo "GCS Bucket: ${GCS_BUCKET}" | tee -a /var/log/startup-script.log
