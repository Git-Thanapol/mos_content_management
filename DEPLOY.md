# MOS CMS — Deployment Guide

ขั้นตอนการ deploy และ update บน Ubuntu Server + Nginx + Docker

---

## สารบัญ

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [First-time Deploy](#first-time-deploy)
4. [Update Deploy](#update-deploy)
5. [สคริปอ้างอิง](#สคริปอ้างอิง)
6. [Management Commands](#management-commands)
7. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
Internet (port 80)
    │
    ▼
 Nginx
    ├── /uploads/*  ──► serve static files โดยตรง (bind mount: /srv/mos-cms/uploads/)
    └── /*          ──► proxy_pass ► Gunicorn :8000 (ใน Docker)
                                         │
                                         ▼
                                   mos-web container
                                   (Django + Gunicorn)
                                         │
                                         ▼
                                   mos-db container
                                   (PostgreSQL 16, internal only)
```

- **Static files** (`/static/`) — ให้ WhiteNoise จัดการภายใน Django ไม่ต้องตั้ง Nginx
- **Media uploads** (`/uploads/`) — bind mount ไปที่ `/srv/mos-cms/uploads/` ให้ Nginx serve โดยตรง
- **PostgreSQL** — ไม่ expose port ออกสู่ภายนอกใน production

---

## Prerequisites

| รายการ | รายละเอียด |
|---|---|
| OS | Ubuntu 22.04 LTS |
| Server spec | 1 vCPU, 1 GB RAM, 20 GB SSD (ขั้นต่ำ) |
| Access | Root SSH |
| Repository | clone ได้จาก server (public repo หรือมี deploy key) |

---

## First-time Deploy

### ขั้นตอนสรุป

```
1. setup.sh     → ติดตั้ง Docker + Nginx + Firewall
2. clone repo   → /srv/mos-cms
3. แก้ .env     → ใส่ค่า production
4. แก้ nginx    → ใส่ server IP/domain
5. deploy.sh --first-run  → build + start + migrate + seed + createsuperuser
6. ตั้ง Group ใน /admin
```

---

### Step 1 — Setup Server (ครั้งเดียว)

SSH เข้า server ในฐาน root แล้วรัน:

```bash
bash deploy/setup.sh
```

สคริปนี้จะ:
- ติดตั้ง Docker CE + Docker Compose plugin
- ติดตั้ง Nginx
- ตั้ง UFW firewall (เปิด SSH + HTTP)
- สร้างโฟลเดอร์ `/srv/mos-cms`

---

### Step 2 — Clone Repository

```bash
git clone https://github.com/Git-Thanapol/mos_content_management.git /srv/mos-cms
cd /srv/mos-cms
```

---

### Step 3 — ตั้งค่า Environment

```bash
cp .env.example .env
nano .env
```

ค่าที่ต้องแก้สำหรับ production:

```env
# Django
DEBUG=False
SECRET_KEY=<สร้างด้วยคำสั่งด้านล่าง>
ALLOWED_HOSTS=<server-ip หรือ domain>

# Database (mos-db container)
DB_NAME=producttest
DB_USER=producttest
DB_PASSWORD=<รหัสผ่านที่แข็งแรง>
DB_HOST=mos-db
DB_PORT=5432

# JST Database (ถ้ามี)
JST_HOST=<jst-host>
JST_PORT=5433
JST_USERNAME=<jst-user>
JST_PASSWORD=<jst-password>
JST_DBNAME=jst
JST_BASE_URL=http://<jst-server-ip>:<port>
```

สร้าง SECRET_KEY:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

---

### Step 4 — ตั้งค่า Nginx

```bash
cp deploy/nginx.conf /etc/nginx/sites-available/mos-cms
nano /etc/nginx/sites-available/mos-cms
```

แก้บรรทัด `server_name`:
```nginx
server_name 1.2.3.4;        # ใช้ IP
# หรือ
server_name yourdomain.com; # ใช้ domain
```

เปิดใช้งาน site:
```bash
ln -sf /etc/nginx/sites-available/mos-cms /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
```

---

### Step 5 — First Deploy

```bash
bash /srv/mos-cms/deploy/deploy.sh --first-run
```

สคริปจะทำ:
1. `git pull` — ดึงโค้ดล่าสุด
2. `docker compose build` — build image
3. `docker compose up -d` — start containers
4. `python manage.py migrate` — run migrations (อัตโนมัติใน container)
5. `python manage.py setup_groups` — สร้าง permission groups
6. `python manage.py seed` — seed ข้อมูลพนักงาน + ตัวอย่าง
7. `python manage.py seed_graphicqueue` — seed media types
8. `python manage.py createsuperuser` — สร้าง admin account (interactive)

---

### Step 6 — ตั้ง User Permissions

เข้า `/admin → Users → <user> → Groups` แล้วเพิ่ม group:

| Group | สิทธิ์ที่ได้ |
|---|---|
| `access_producttest` | เข้าระบบ Product Test Center |
| `access_clearance` | เข้าระบบสินค้าโล๊ะ |
| `access_graphicqueue` | เข้าระบบคิวงานกราฟิก |
| `supervisor` | ฟีเจอร์ supervisor ใน Product Test |
| `employee` | role พนักงานทั่วไป |

> Superuser ผ่านทุก access check โดยอัตโนมัติ

---

## Update Deploy

เมื่อมีโค้ดใหม่ถูก push ขึ้น `main`:

```bash
cd /srv/mos-cms
bash deploy/deploy.sh
```

สคริปจะทำ:
1. `git pull` — ดึงโค้ดใหม่
2. `docker compose build` — rebuild image
3. `docker compose up -d` — restart containers (DB ไม่ restart ถ้าไม่มีการเปลี่ยน)
4. migrate รันอัตโนมัติตอน container start
5. `setup_groups` — sync groups (safe to re-run)
6. reload Nginx

### ถ้ามี Migration ใหม่

Migration รันอัตโนมัติใน Dockerfile CMD:
```dockerfile
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn ..."]
```
ไม่ต้องรันเองถ้าใช้ `deploy.sh`

### ถ้ามี Media Type ใหม่ (graphicqueue)

```bash
cd /srv/mos-cms
docker compose -f docker-compose.prod.yml exec mos-web python manage.py seed_graphicqueue
```

> ใช้ `--flush` เฉพาะเมื่อต้องการล้างและ re-seed ทั้งหมด (ลบ M2M links ด้วย)

---

## สคริปอ้างอิง

### `deploy/setup.sh`
```
ใช้ครั้งเดียวบน fresh server
รัน: bash deploy/setup.sh
ติดตั้ง: Docker, Nginx, UFW firewall
```

### `deploy/deploy.sh`
```
ใช้สำหรับ deploy ครั้งแรกและ update ทุกครั้ง

bash deploy/deploy.sh              # update deploy
bash deploy/deploy.sh --first-run  # first-time (seed + createsuperuser)
```

### `deploy/nginx.conf`
```
Nginx reverse proxy config
แก้ server_name ก่อน copy ไปที่ /etc/nginx/sites-available/mos-cms
```

---

## Management Commands

รันผ่าน `docker compose exec` บน production:

```bash
# prefix สำหรับ production
EXEC="docker compose -f /srv/mos-cms/docker-compose.prod.yml exec mos-web"

# Seed / reset data
$EXEC python manage.py seed
$EXEC python manage.py seed --flush          # ล้างและ reseed
$EXEC python manage.py setup_groups          # sync permission groups
$EXEC python manage.py seed_graphicqueue     # เพิ่ม media types ที่ขาด
$EXEC python manage.py seed_graphicqueue --flush  # ล้างและ reseed media types

# Database
$EXEC python manage.py migrate               # รัน migrations (ปกติอัตโนมัติ)
$EXEC python manage.py showmigrations        # ดู migration status

# Admin
$EXEC python manage.py createsuperuser       # สร้าง superuser

# Logs
docker compose -f /srv/mos-cms/docker-compose.prod.yml logs mos-web -f
```

---

## Troubleshooting

### Container ไม่ start

```bash
cd /srv/mos-cms
docker compose -f docker-compose.prod.yml logs mos-web
docker compose -f docker-compose.prod.yml logs mos-db
```

### Web ตอบช้าหรือ 502 Bad Gateway

```bash
# ตรวจ Gunicorn ยังรันอยู่ไหม
docker compose -f docker-compose.prod.yml ps

# Restart web container
docker compose -f docker-compose.prod.yml restart mos-web

# Rebuild ถ้าดึงโค้ดใหม่
docker compose -f docker-compose.prod.yml up -d --build
```

### Migration error ตอน start

```bash
# ดู error log
docker compose -f docker-compose.prod.yml logs mos-web | grep -i error

# รัน migrate ด้วยมือ
docker compose -f docker-compose.prod.yml exec mos-web python manage.py migrate
```

### Nginx 403/404 สำหรับ /uploads/

```bash
# ตรวจสิทธิ์โฟลเดอร์
ls -la /srv/mos-cms/uploads/

# แก้สิทธิ์ถ้าจำเป็น
chmod -R 755 /srv/mos-cms/uploads/
```

### เช็ค disk space

```bash
df -h
docker system df          # Docker images/volumes
docker system prune -f    # ลบ images เก่าที่ไม่ใช้
```

---

## Quick Reference

```bash
# ─── Daily Ops ───────────────────────────────────────────────
cd /srv/mos-cms

docker compose -f docker-compose.prod.yml ps           # ดูสถานะ
docker compose -f docker-compose.prod.yml logs -f      # ดู logs
docker compose -f docker-compose.prod.yml restart mos-web  # restart

# ─── Deploy update ───────────────────────────────────────────
bash deploy/deploy.sh

# ─── Emergency restart ───────────────────────────────────────
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d
```
