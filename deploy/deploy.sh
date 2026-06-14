#!/usr/bin/env bash
# Deploy or update MOS CMS.
# Usage:
#   bash deploy/deploy.sh             # update existing deploy
#   bash deploy/deploy.sh --first-run # first-time: also seeds data + creates superuser
set -euo pipefail

APP_DIR="/opt/mos-cms"
COMPOSE="docker compose -f docker-compose.prod.yml"
FIRST_RUN=false

for arg in "$@"; do
  [[ "$arg" == "--first-run" ]] && FIRST_RUN=true
done

cd "$APP_DIR"

# Verify .env exists
if [[ ! -f .env ]]; then
  echo "ERROR: .env not found. Copy .env.example and fill in production values."
  exit 1
fi

echo "==> Pulling latest code..."
git pull

echo "==> Creating uploads directory..."
mkdir -p uploads

echo "==> Building image..."
$COMPOSE build

echo "==> Starting containers..."
$COMPOSE up -d

echo "==> Waiting for web container to be ready..."
sleep 5

echo "==> Running setup_groups..."
$COMPOSE exec mos-web python manage.py setup_groups

if [[ "$FIRST_RUN" == true ]]; then
  echo "==> Seeding initial data..."
  $COMPOSE exec mos-web python manage.py seed
  $COMPOSE exec mos-web python manage.py seed_graphicqueue

  echo ""
  echo "==> Create your admin account:"
  $COMPOSE exec -it mos-web python manage.py createsuperuser
fi

echo "==> Reloading Nginx..."
nginx -t && systemctl reload nginx

echo ""
echo "Done! App is running."
$COMPOSE ps
