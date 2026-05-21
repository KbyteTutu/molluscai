#!/usr/bin/env bash
set -euo pipefail

echo "# MolluscAI — generated $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo

# JWT secrets (64 chars each)
echo "JWT_SECRET_KEY=$(openssl rand -hex 32)"
echo "JWT_REFRESH_SECRET_KEY=$(openssl rand -hex 32)"

# AES encryption key (32 bytes = 64 hex chars)
echo "ENCRYPTION_KEY=$(openssl rand -hex 32)"

# Database
echo "POSTGRES_USER=mollusc"
echo "POSTGRES_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=')"
echo "POSTGRES_DB=molluscai"

# MinIO
echo "MINIO_ROOT_USER=minioadmin"
echo "MINIO_ROOT_PASSWORD=$(openssl rand -base64 18 | tr -d '/+=')"
