# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**MOS CMS** — a Thai e-commerce content management system for a product team (employees: เบ้น, บอส, มอส, แก้ว, ฟาง). Single Django project at the repo root; each business domain is a Django app under `apps/`. Mockup `.html` files at the root are the **reference spec — never modify them**.

## Project Structure

```
mos_content_management/          ← repo root = Django project root
├── docker-compose.yml           # mos-db (postgres:16) + mos-web (Django)
├── Dockerfile
├── manage.py
├── requirements.txt
├── .env / .env.example
├── config/                      # Django settings, urls, wsgi, asgi
├── apps/
│   ├── accounts/                # login/logout
│   ├── core/                    # hub view, system registry, access decorator, context processor
│   ├── producttest/             # Phase 1: Product Test System
│   └── clearance/               # Phase 2: Clearance Products (reads JST DB)
├── templates/
│   ├── base.html                # system-agnostic top bar + shared JS/modal infra
│   ├── core/hub.html
│   ├── accounts/login.html
│   ├── producttest/             # page templates + _base.html (subnav)
│   └── clearance/               # page templates + _base.html (subnav)
├── static/                      # vendored / project-wide static files
├── uploads/                     # MEDIA_ROOT (Docker volume mos-media, gitignored)
└── *.html                       # mockup reference files — READ ONLY
```

New phases are added as Django apps under `apps/`. No new subfolders.

## Dev Setup (Docker required)

```bash
# First time
cp .env.example .env            # defaults already work for Docker
docker compose up --build -d    # mos-db on :5434, mos-web on :8000
docker compose exec mos-web python manage.py migrate
docker compose exec mos-web python manage.py setup_groups
docker compose exec mos-web python manage.py seed
docker compose exec mos-web python manage.py createsuperuser

# Daily
docker compose up -d
docker compose down
docker compose logs mos-web -f
```

After `createsuperuser`, in `/admin → Users → your user → Groups`:
- Add `supervisor` for full producttest supervisor access
- Add `access_producttest` to access Product Test Center
- Add `access_clearance` to access Clearance Products
- Superusers bypass all access checks (see all systems automatically)

## Management Commands

| Command | Purpose |
|---|---|
| `python manage.py seed` | Seed 5 employees + 3 sample products + groups |
| `python manage.py seed --flush` | Wipe app data then reseed |
| `python manage.py setup_groups` | Create all groups (`employee`, `supervisor`, `access_*`) |

## Stack

- **Backend:** Django 5.0, Python 3.12
- **Frontend:** Django Templates + HTMX + Bootstrap 5 (server-rendered; HTMX for table/filter fragment swaps)
- **DB (default):** PostgreSQL 16 via `mos-db` container (host port `5434`)
- **DB (jst):** External JST PostgreSQL at `JST_HOST:JST_PORT` — read-only, routed by `JstRouter`
- **Storage:** `MEDIA_ROOT = uploads/` (Docker volume `mos-media`), swappable to S3 via `django-storages`
- **Auth:** Django built-in sessions + Groups

## Multi-System Hub & Access (`apps/core/`)

After login, `/` shows the **hub** — a card for each system the user may access.

### System registry (`apps/core/access.py`)
`SYSTEMS` list defines key, name, icon, color, url_name, group for each system.

### Access model
| Group | Purpose |
|---|---|
| `access_producttest` | Access to Product Test Center (`/producttest/`) |
| `access_clearance` | Access to Clearance Products (`/clearance/`) |
| `supervisor` | Supervisor features within producttest |
| `employee` | Standard employee role |

Assign in `/admin → Users → Groups`. Superusers pass all checks.

### View decorator
`@system_required("key")` in `apps/core/access.py`:
- Unauthenticated → redirect to login
- Authenticated, no access → 403

### URL map
| Prefix | App | Notes |
|---|---|---|
| `/` | `apps.core` | Hub (login-required) |
| `/producttest/` | `apps.producttest` | No URL namespace; names unchanged |
| `/clearance/` | `apps.clearance` | namespace = `clearance` |
| `/accounts/` | `apps.accounts` | login/logout |

## Phase 1 — Product Test System (`apps/producttest/`)

**Reference mockup:** `สินค้า TEST 5.6.2026.html`

### Data model

| Model | Key fields |
|---|---|
| `Employee` | `name`, `is_graphic`, `is_mkt`, `is_active` |
| `TestProduct` | `pid`, `name`, `upload_date`, `start_date`, `end_date`, `manual_status`, M2M graphic/mkt members |
| `TestPrice` | FK product, `value`, `order` |
| `ProductPage` | FK product, `page`, `url`, `order` |
| `Performance` | 1-to-1 product, `orders`, `sales`, `ads`, `profit` |
| `Commission` | 1-to-1 product, `total`, `per_person` (auto-computed), `status`, `note` |
| `CommissionSlip` | FK commission, `image` (multi-file upload) |

### `computed_status()` logic (mirrors `getComputedStatus` in mockup)
Locked manual statuses (`กำลังดำเนินการ / Test ผ่าน / Test ไม่ผ่าน / ยกเลิก`) take precedence.
Otherwise: no members → `รอดำเนินการ`; any member assigned → `กำลังดำเนินการ`.

### URLs (prefix `/producttest/`, no namespace)

| URL | View | Access |
|---|---|---|
| `/producttest/` | `product_list` | `access_producttest` |
| `/producttest/supervisor/` | `supervisor_view` | `access_producttest` + `supervisor` |
| `/producttest/report/` | `personal_report` | `access_producttest` |
| `/producttest/employees/` | `employee_list` | `access_producttest` + `supervisor` |
| `/producttest/htmx/*` | HTMX partial endpoints | same as parent view |

### Template tags (`apps/producttest/templatetags/producttest_tags.py`)
- `is_supervisor_filter` — used in `producttest/_base.html` subnav to gate supervisor links
- `format_decimal` — locale-formatted number
- `thai_date` — `dd/mm/yyyy` format

## Phase 2 — Clearance Products (`apps/clearance/`)

**Reference mockup:** `ระบบสินค้าโล๊ะ.html`

### JST integration (read-only)

Live data pulled from JST Management System PostgreSQL (external, connection in `.env`):

| JST table | Fields used | Purpose |
|---|---|---|
| `inventory_masteritem` | `product_code`, `name` | SKU search, name cache |
| `inventory_jststocksnapshot` | `quantity`, `snapshot_date` | สต็อกคงเหลือ (latest per SKU) |
| `inventory_poheader` | `order_date`, `shipping_rate_thb_cbm` | วันที่สั่งซื้อล่าสุด |
| `inventory_poitem` | `qty_ordered`, `price_baht`, `total_received_cbm` | ต้นทุน (landed unit cost) |

Mirror models in `apps/clearance/jst_models.py` (`managed=False`).
Router in `apps/clearance/routers.py` routes them to the `jst` DB.
Service layer `apps/clearance/jst.py`: `search_products(q)` and `enrich(codes)` — both fail-safe.

**Landed unit cost** = `(price_baht + total_received_cbm × header.shipping_rate_thb_cbm) / qty_ordered`

### Data model (own DB)

| Model | Key fields |
|---|---|
| `ClearanceProduct` | `product_code` (JST SKU), `product_name` (cached), `status`, `assignee`, `process_date`, `done_date` |
| `ClearancePromo` | FK product, `old_price`, `new_price`, `order` |

Stock/cost/last_order_date are fetched live from JST, never stored.

### JST product picker (add modal)
1. User types in the search box → HTMX → `jst_search` → `jst_options.html` dropdown
2. User clicks a result → JS sets `product_code` + `product_name` (hidden) → HTMX → `jst_fields.html` (read-only info)
3. On save, view refreshes name from JST; falls back to hidden form field if JST down

### URLs (prefix `/clearance/`, namespace `clearance`)

| URL | View |
|---|---|
| `clearance:clearance_list` | Main list + stat cards |
| `clearance:clearance_table_partial` | HTMX rows (status + search filter + JST enrich) |
| `clearance:clearance_add` / `clearance_edit` | Add/edit modal |
| `clearance:clearance_delete` | POST delete |
| `clearance:promo_modal` | Old→new price promotion editor |
| `clearance:jst_search` | HTMX SKU search autocomplete |
| `clearance:jst_fields` | HTMX read-only JST info block |

## Environment Variables (`.env`)

| Variable | Used by |
|---|---|
| `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` | Django |
| `DB_NAME/USER/PASSWORD/HOST/PORT` | Default DB (`mos-db` container) |
| `JST_HOST/PORT/USERNAME/PASSWORD/DBNAME` | JST read-only DB (Clearance app) |

## Mockup Reference Notes

- Status badge colors: รอดำเนินการ = secondary, กำลังดำเนินการ = warning, ผ่าน/เรียบร้อย = success, ไม่ผ่าน = danger, ยกเลิก = dark
- Profit column: **red when negative, green when positive** (`Performance.profit_is_negative`)
- Commission per-person is always auto-split: `total ÷ (graphic_count + mkt_count)`
- เบ้น is both Graphic and MKT — modelled as two boolean fields on `Employee`, not a single role field

## Roles

- **Graphic team**: บอส, มอส, เบ้น
- **MKT team**: เบ้น, แก้ว, ฟาง

## Phase 3 — Graphic Queue (`apps/graphicqueue/`)

**Reference mockup:** `ระบบลงคิวงานกราฟฟิก.html`

### Data model

| Model | Key fields |
|---|---|
| `MediaType` | `name` (unique), `category` (`video`/`image`), `order` — dynamic catalog |
| `GraphicJob` | `sku`, `name`, `image`, `status`, `urgency`, `product_type`, `assignee` (FK Employee graphic team), `order_date`, `deadline`, `submit_date`, `work_url`, M2M `media_types` |
| `RefImage` | FK `job`, `image`, `brief` (1-to-1 text per image), `order` |

`GraphicJob.work_days` property = `(submit_date − order_date).days` when both set.

### Dynamic media catalog
Media types start empty and grow as users add them via freetext. `seed_graphicqueue` pre-seeds the 10 types from the mockup. On add/edit form, a freetext input below the checkboxes creates a new `MediaType` via HTMX POST and the checkbox list refreshes immediately with the new type pre-checked.

### Reference images (1-to-1 brief)
Each uploaded reference image has its own `brief` text field. Different from the mockup's single textarea — matches `Requirement.md`.

### URLs (prefix `/graphicqueue/`, namespace `graphicqueue`)

| URL | View |
|---|---|
| `graphicqueue:queue_list` | Main list + stat cards |
| `graphicqueue:queue_table_partial` | HTMX rows |
| `graphicqueue:queue_add` / `queue_edit` | Add/edit modal |
| `graphicqueue:queue_delete` | POST delete |
| `graphicqueue:view_media` | Read-only media list modal |
| `graphicqueue:view_ref` | Read-only ref images + briefs modal |
| `graphicqueue:media_type_add` | HTMX POST: add new media type |

### Management commands
| Command | Purpose |
|---|---|
| `python manage.py seed_graphicqueue` | Seed 10 default media types (5 video + 5 image) |

## Phase 4 — Page Manager (`apps/pagemanager/`)

**Reference files:** `page_product_manager (2).html` (PageFlow mockup — page list UI), `ระบบ (2).xlsx` (post-log spreadsheet the team currently fills by hand)

### Data model

| Model | Key fields |
|---|---|
| `FacebookPage` | `page_name`, `page_id` (unique, numeric), `status` (6 fixed choices), M2M `owners` (Employee — controls visibility), `note` |
| `PageSKU` | FK `page`, `product_code`/`product_name` (JST SKU, cached), `order` — 1 page can have many SKUs |
| `PostMediaType` | `name` (unique), `order` — dynamic catalog, freetext-add like `graphicqueue.MediaType` |
| `PagePost` | FK `page`, `image`, `poster` (FK Employee), `product_code`/`product_name` (JST SKU), `media_type`, `post_id` (numeric), `post_date`, `note`, `supervisor_note` |

SKU fields on both `FacebookPage`/`PagePost` reuse `apps/clearance/jst.py` (`search_products`, `enrich`) — no separate JST integration code.

### Row-level access (`apps/pagemanager/scoping.py`)
Non-supervisor employees see only pages where they're listed in `owners` (resolved via `request.user.employee`, the existing `Employee.user` OneToOne). Supervisors (group `supervisor`) and superusers see everything. Every view/export filters through `visible_pages(user)` — never `FacebookPage.objects.all()` directly. `PagePost.supervisor_note` is stripped from the form, template, and Excel export for non-supervisors (three independent layers).

### URLs (prefix `/pagemanager/`, namespace `pagemanager`)

| URL | View |
|---|---|
| `pagemanager:page_list` / `page_table_partial` | Page list + stat cards, scoped by `visible_pages` |
| `pagemanager:page_add` / `page_edit` / `page_delete` | Supervisor-only; syncs `PageSKU` + `owners` |
| `pagemanager:jst_search` | HTMX SKU autocomplete (multi-select chips) |
| `pagemanager:post_list` / `post_table_partial` | Posts within one page |
| `pagemanager:post_add` / `post_edit` / `post_delete` | Post CRUD, scoped through the parent page |
| `pagemanager:media_type_add` | HTMX POST: add new post media type |
| `pagemanager:export_pages` / `export_all_posts` / `export_page_posts` | `.xlsx` exports via `apps/pagemanager/exports.py` (openpyxl), all scoped by `visible_pages` |

### Management commands
| Command | Purpose |
|---|---|
| `python manage.py seed_pagemanager` | Seed 6 default post media types from the source spreadsheet |

## Upcoming Phases

| Phase | App (planned) | Purpose |
|---|---|---|
| 5 | `apps/access` | Cross-system role & access management |
