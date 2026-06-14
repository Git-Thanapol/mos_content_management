#!/usr/bin/env bash
# Run once as root on a fresh Ubuntu server.
# Usage: bash deploy/setup.sh
set -euo pipefail

APP_DIR="/srv/mos-cms"

echo "==> Installing Docker..."
apt-get update -qq
apt-get install -y -qq ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update -qq
apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin

echo "==> Installing Nginx..."
apt-get install -y -qq nginx

echo "==> Configuring firewall..."
ufw allow OpenSSH
ufw allow 'Nginx HTTP'
ufw --force enable

echo "==> Creating app directory..."
mkdir -p "$APP_DIR"

echo ""
echo "Setup complete. Next steps:"
echo ""
echo "  1. Clone the repo:"
echo "       git clone <your-repo-url> $APP_DIR"
echo ""
echo "  2. Create production .env:"
echo "       cd $APP_DIR"
echo "       cp .env.example .env"
echo "       nano .env"
echo "     Set: DEBUG=False, SECRET_KEY=<random>, ALLOWED_HOSTS=<server-ip>"
echo "          DB_HOST=mos-db, DB_PORT=5432"
echo ""
echo "  3. Install Nginx config:"
echo "       cp deploy/nginx.conf /etc/nginx/sites-available/mos-cms"
echo "       nano /etc/nginx/sites-available/mos-cms   # set server_name"
echo "       ln -sf /etc/nginx/sites-available/mos-cms /etc/nginx/sites-enabled/"
echo "       rm -f /etc/nginx/sites-enabled/default"
echo "       nginx -t && systemctl reload nginx"
echo ""
echo "  4. First deploy:"
echo "       bash $APP_DIR/deploy/deploy.sh --first-run"
