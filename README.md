# MOS CMS

Thai e-commerce content management system for the MOS product team.

## Stack

- **Backend:** Django 5.0, Python 3.12
- **Frontend:** Django Templates + HTMX + Bootstrap 5
- **Database:** PostgreSQL 16
- **Containerization:** Docker + Docker Compose

---

## Local Development

**Requirements:** Docker Desktop

```bash
# 1. Clone and configure
git clone https://github.com/Git-Thanapol/mos_content_management.git
cd mos_content_management
cp .env.example .env          # defaults work as-is for Docker

# 2. Start containers
docker compose up --build -d

# 3. Initialize database
docker compose exec mos-web python manage.py migrate
docker compose exec mos-web python manage.py setup_groups
docker compose exec mos-web python manage.py seed
docker compose exec mos-web python manage.py seed_graphicqueue
docker compose exec mos-web python manage.py createsuperuser

# 4. Open http://localhost:8000
```

After creating a superuser, assign groups in `/admin → Users → your user → Groups`:
- `access_producttest` — Product Test Center
- `access_clearance` — Clearance Products
- `supervisor` — Supervisor features within Product Test

Superusers bypass all access checks automatically.

### Daily commands

```bash
docker compose up -d            # start
docker compose down             # stop
docker compose logs mos-web -f  # view logs
```

---

## Production Deployment (Ubuntu + Nginx + Gunicorn)

### Requirements

- Ubuntu 22.04 VPS (minimum 1 vCPU, 1 GB RAM, 20 GB SSD)
- Root SSH access
- Git repository access from the server

---

### Step 1 — Server setup (run once)

SSH into the server as root, then run the setup script:

```bash
bash deploy/setup.sh
```

This installs Docker, Nginx, and configures the UFW firewall (allows SSH + HTTP).

---

### Step 2 — Clone the repository

```bash
git clone https://github.com/Git-Thanapol/mos_content_management.git /srv/mos-cms
cd /srv/mos-cms
```

---

### Step 3 — Configure environment

```bash
cp .env.example .env
nano .env
```

Set these values for production:

```env
DEBUG=False
SECRET_KEY=<generate a long random string>
ALLOWED_HOSTS=<your-server-ip-or-domain>

DB_NAME=producttest
DB_USER=producttest
DB_PASSWORD=<strong-password>
DB_HOST=mos-db
DB_PORT=5432

JST_HOST=<jst-db-host>
JST_PORT=5433
JST_USERNAME=<jst-user>
JST_PASSWORD=<jst-password>
JST_DBNAME=jst
```

Generate a secret key:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

---

### Step 4 — Configure Nginx

```bash
cp deploy/nginx.conf /etc/nginx/sites-available/mos-cms
nano /etc/nginx/sites-available/mos-cms
```

Edit `server_name` to your server IP or domain:
```nginx
server_name 1.2.3.4;  # or: server_name yourdomain.com;
```

Then enable the site:
```bash
ln -sf /etc/nginx/sites-available/mos-cms /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
```

---

### Step 5 — First deploy

```bash
bash /srv/mos-cms/deploy/deploy.sh --first-run
```

This will:
1. Build the Docker image
2. Start `mos-db` (PostgreSQL) and `mos-web` (Gunicorn) containers
3. Run migrations
4. Run `setup_groups`, `seed`, `seed_graphicqueue`
5. Prompt you to create a superuser

---

### Updating the app

```bash
cd /srv/mos-cms
bash deploy/deploy.sh
```

This pulls the latest code, rebuilds the image, and restarts containers with zero-downtime for the database.

---

### Restarting Gunicorn

```bash
cd /srv/mos-cms
docker compose -f docker-compose.prod.yml restart mos-web
```

If you pulled new code and need a full rebuild:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

---

### Architecture overview

```
Internet → Nginx :80
              ├── /uploads/*  → served directly from /srv/mos-cms/uploads/
              └── /*          → proxy to Gunicorn :8000 (inside Docker)
                                    └── mos-web container
                                          └── mos-db container (PostgreSQL, internal only)
```

- **Static files** (`/static/`) are served by WhiteNoise inside Django — no Nginx rule needed.
- **Media uploads** (`/uploads/`) are stored in `/srv/mos-cms/uploads/` (bind mount) and served directly by Nginx.
- PostgreSQL is **not exposed** to the host network in production.

---

### Management commands

| Command | Purpose |
|---|---|
| `python manage.py seed` | Seed 5 employees + sample products |
| `python manage.py seed --flush` | Wipe app data and reseed |
| `python manage.py setup_groups` | Create all permission groups |
| `python manage.py seed_graphicqueue` | Seed 10 default media types |
