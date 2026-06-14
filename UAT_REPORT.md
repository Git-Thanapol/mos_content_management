# UAT Test Report — MOS CMS

| | |
|---|---|
| **Project** | mos_content_management |
| **Date** | 2026-06-05 |
| **Environment** | Django 5.0.6 · Python 3.12 · PostgreSQL 16 (Docker `mos-db`) |
| **Command** | `docker compose exec mos-web python manage.py test apps --verbosity 2` |
| **Result** | ✅ **Ran 122 tests — 122 passed / 0 failed** (44.99 s) |

> Note: The `jst` database (read-only external host `103.114.201.9`) is skipped automatically during testing via `"TEST": {"MIRROR": "default"}` in settings. All JST service calls are mocked at the view/service layer — no external network traffic.

---

## Core — Auth, Hub & Multi-System Access

| Case ID | Scenario | Steps | Expected | Result |
|---------|----------|-------|----------|--------|
| CORE-01 | Hub unauthenticated | GET `/` without login | 302 → `/accounts/login/?next=/` | ✅ |
| CORE-02 | ProductTest unauthenticated | GET `/producttest/` without login | 302 with `?next=` | ✅ |
| CORE-03 | Clearance unauthenticated | GET `/clearance/` without login | 302 with `?next=` | ✅ |
| CORE-04 | GraphicQueue unauthenticated | GET `/graphicqueue/` without login | 302 with `?next=` | ✅ |
| CORE-05 | No-group user — ProductTest | Login user with no groups, GET `/producttest/` | 403 Forbidden | ✅ |
| CORE-06 | No-group user — Clearance | Login user with no groups, GET `/clearance/` | 403 Forbidden | ✅ |
| CORE-07 | No-group user — GraphicQueue | Login user with no groups, GET `/graphicqueue/` | 403 Forbidden | ✅ |
| CORE-08a | access_producttest allows producttest | Login `access_producttest` user, GET `/producttest/` | 200 OK | ✅ |
| CORE-08b | access_producttest blocked from clearance | Same user, GET `/clearance/` | 403 Forbidden | ✅ |
| CORE-08c | access_producttest blocked from graphicqueue | Same user, GET `/graphicqueue/` | 403 Forbidden | ✅ |
| CORE-09 | access_clearance allows clearance | Login `access_clearance` user, GET `/clearance/` | 200 OK | ✅ |
| CORE-10 | access_graphicqueue allows graphicqueue | Login `access_graphicqueue` user, GET `/graphicqueue/` | 200 OK | ✅ |
| CORE-11a | Superuser — ProductTest | Login superuser, GET `/producttest/` | 200 OK | ✅ |
| CORE-11b | Superuser — Clearance | Login superuser, GET `/clearance/` | 200 OK | ✅ |
| CORE-11c | Superuser — GraphicQueue | Login superuser, GET `/graphicqueue/` | 200 OK | ✅ |
| CORE-12a | Hub cards — no groups | Login no-group user, GET `/` | 0 system cards | ✅ |
| CORE-12b | Hub cards — one group | Login `access_producttest` user, GET `/` | 1 card (producttest) | ✅ |
| CORE-12c | Hub cards — superuser | Login superuser, GET `/` | 3 cards (all systems) | ✅ |
| CORE-13a | AnonymousUser cannot access | Call `user_can_access(AnonymousUser, "producttest")` | Returns `False` | ✅ |
| CORE-13b | Unknown system key | Call `user_can_access(user, "does_not_exist")` | Returns `False` (no exception) | ✅ |
| CORE-13c | Superuser gets all systems | Call `accessible_systems(superuser)` | Returns all 3 system keys | ✅ |
| CORE-13d | SYSTEMS registry integrity | Check each entry in `SYSTEMS` list | All entries have required keys | ✅ |
| CORE-14a | Login page loads | GET `/accounts/login/` | 200 OK | ✅ |
| CORE-14b | Valid login redirects | POST valid credentials | 302 → hub | ✅ |
| CORE-14c | Invalid login re-renders | POST bad password | 200 (form with error) | ✅ |
| CORE-14d | Logout redirects | POST `/accounts/logout/` | 302 → `/accounts/login/` | ✅ |
| CORE-15a | setup_groups creates groups | Run `setup_groups` command | All 5 groups exist in DB | ✅ |
| CORE-15b | setup_groups is idempotent | Run `setup_groups` twice | No duplicates, no error | ✅ |

---

## Phase 1 — Product Test System

### Model Tests

| Case ID | Scenario | Steps | Expected | Result |
|---------|----------|-------|----------|--------|
| PT-01 | computed_status — no members | Create product with no members, manual=auto | `"รอดำเนินการ"` | ✅ |
| PT-02 | computed_status — graphic member | Assign graphic member, manual=auto | `"กำลังดำเนินการ"` | ✅ |
| PT-03 | computed_status — manual IN_PROGRESS wins | manual=กำลังดำเนินการ, no members | `"กำลังดำเนินการ"` | ✅ |
| PT-04 | computed_status — manual PASS wins | manual=Test ผ่าน, member assigned | `"Test ผ่าน"` | ✅ |
| PT-05 | computed_status — manual FAIL wins | manual=Test ไม่ผ่าน | `"Test ไม่ผ่าน"` | ✅ |
| PT-06 | computed_status — manual CANCEL wins | manual=ยกเลิก | `"ยกเลิก"` | ✅ |
| PT-07 | test_days — 10 days | start=Jan 1, end=Jan 11 | Returns `10` | ✅ |
| PT-08 | test_days — min 1 | start=end (same day) | Returns `1` | ✅ |
| PT-09 | test_days — no end_date | No end_date set | Returns `None` | ✅ |
| PT-10 | member_count — combined | 2 graphic + 1 mkt | Returns `3` | ✅ |
| PT-11 | member_count — zero | No members | Returns `0` | ✅ |
| PT-12 | Commission auto-split | total=3000, 3 members | per_person=1000.00 | ✅ |
| PT-13 | Commission zero-members guard | total=5000, 0 members | per_person=0 (no ZeroDivisionError) | ✅ |
| PT-14 | profit_is_negative — negative | profit=-100 | Returns `True` | ✅ |
| PT-15 | profit_is_negative — positive | profit=100 | Returns `False` | ✅ |
| PT-16 | ads_pct calculation | ads=500, sales=2000 | Returns `25.0` | ✅ |
| PT-17 | ads_pct zero-sales guard | sales=0 | Returns `0.0` (no ZeroDivisionError) | ✅ |
| PT-18 | profit_pct calculation | profit=400, sales=2000 | Returns `20.0` | ✅ |

### View Tests

| Case ID | Scenario | Steps | Expected | Result |
|---------|----------|-------|----------|--------|
| PT-19 | product_list 200 | GET `/producttest/` | 200 OK | ✅ |
| PT-20 | stat_cards in context | GET `/producttest/` | `stat_cards` present | ✅ |
| PT-21 | table partial 200 | GET `/producttest/htmx/products/` | 200 OK | ✅ |
| PT-22 | search filter | GET `?q=Alpha` | Returns only "Alpha" | ✅ |
| PT-23 | status filter | GET `?status=รอดำเนินการ` | Returns only no-member products | ✅ |
| PT-24 | product_add GET | GET `/producttest/products/add/` | 200 OK modal | ✅ |
| PT-25 | product_add POST | POST form with prices_json + pages_json | Creates TestProduct + Performance + Commission + 2 prices + 1 page | ✅ |
| PT-26 | prices_json skips blank | POST with `["200",""]` | Only 1 price created | ✅ |
| PT-27 | product_edit POST | POST updated name | DB record updated | ✅ |
| PT-28 | product_delete | POST to delete URL | Product removed from DB | ✅ |
| PT-29 | Non-supervisor → supervisor view | Login non-supervisor, GET `/producttest/supervisor/` | 302 redirect (user_passes_test) | ✅ |
| PT-30 | Supervisor → supervisor view | Login supervisor, GET `/producttest/supervisor/` | 200 OK | ✅ |
| PT-31 | Non-supervisor → employee list | Login non-supervisor, GET `/producttest/employees/` | 302 redirect | ✅ |
| PT-32 | Supervisor → employee list | Login supervisor, GET `/producttest/employees/` | 200 OK | ✅ |
| PT-33 | employee_toggle | POST to toggle URL | `is_active` flipped | ✅ |

---

## Phase 2 — Clearance Products (JST Mocked)

### Model Tests

| Case ID | Scenario | Steps | Expected | Result |
|---------|----------|-------|----------|--------|
| CL-01 | status_bs — wait | Product with STATUS_WAIT | Returns `"secondary"` | ✅ |
| CL-02 | status_bs — in_progress | Product with STATUS_IN_PROGRESS | Returns `"warning"` | ✅ |
| CL-03 | status_bs — done | Product with STATUS_DONE | Returns `"success"` | ✅ |
| CL-04 | status_bg_style — wait | Product with STATUS_WAIT | Style contains `#3730a3` (indigo) | ✅ |
| CL-05 | status_bg_style — done | Product with STATUS_DONE | Style contains `#065f46` (emerald) | ✅ |

### Router Tests

| Case ID | Scenario | Steps | Expected | Result |
|---------|----------|-------|----------|--------|
| CL-06 | JstRouter — JST model | `db_for_read(JstMasterItem)` | Returns `"jst"` | ✅ |
| CL-07 | JstRouter — non-JST model | `db_for_read(ClearanceProduct)` | Returns `None` | ✅ |
| CL-08 | JstRouter — block migrate JST | `allow_migrate("jst", ...)` | Returns `False` | ✅ |
| CL-09 | JstRouter — allow migrate default | `allow_migrate("default", ...)` | Returns `None` | ✅ |

### JST Service Tests (No DB)

| Case ID | Scenario | Steps | Expected | Result |
|---------|----------|-------|----------|--------|
| CL-10 | search_products empty query | Call `search_products("")` | Returns `[]` | ✅ |
| CL-11 | enrich empty codes | Call `enrich([])` | Returns `{}` | ✅ |
| CL-12 | enrich swallows exception | Patch backend to raise, call `enrich(["SP001"])` | Returns fallback `{name:"-", stock:"-", last_order_date:None}`, no exception | ✅ |

### View Tests (JST Patched)

| Case ID | Scenario | Steps | Expected | Result |
|---------|----------|-------|----------|--------|
| CL-13 | clearance_list 200 | GET `/clearance/` | 200 OK | ✅ |
| CL-14 | stat_cards in context | GET `/clearance/` | `stat_cards` present | ✅ |
| CL-15 | stats reflect DB counts | Create 1 wait + 1 done, GET `/clearance/` | stats.all=2, stats.done=1 | ✅ |
| CL-16 | table partial 200 | GET `/clearance/htmx/rows/` | 200 OK | ✅ |
| CL-17 | JST data merged into rows | Mock JST name/stock/cost, GET rows | Row has `jst_name="JST Name"`, `jst_stock=30` | ✅ |
| CL-18 | status filter | GET `?status=รอดำเนินการ` | Only waiting products returned | ✅ |
| CL-19 | search filter | GET `?q=SF03` | Only SF03 returned | ✅ |
| CL-20 | clearance_add GET | GET `/clearance/add/` | 200 OK | ✅ |
| CL-21 | clearance_add POST — JST name refresh | Mock JST name, POST add | `product_name` set from JST | ✅ |
| CL-22 | clearance_add POST — JST down | Mock JST returns `"-"`, POST add | `product_name` kept from form field | ✅ |
| CL-23 | clearance_delete | POST to delete URL | Product removed from DB | ✅ |
| CL-24 | promo_modal GET | GET `/<pk>/promos/` | 200 OK | ✅ |
| CL-25 | promo_modal POST — saves rows | POST with 3 rows (1 blank) | 2 promos saved, blank row skipped | ✅ |
| CL-26 | promo_modal POST — replaces old | POST new rows when 1 old exists | Old deleted, only 1 new promo | ✅ |
| CL-27 | jst_search | GET `/clearance/htmx/jst-search/?q=SP` | 200 OK | ✅ |
| CL-28 | jst_fields | GET `/clearance/htmx/jst-fields/?code=SP999` | 200 OK | ✅ |

---

## Phase 3 — Graphic Queue System

### Model Tests

| Case ID | Scenario | Steps | Expected | Result |
|---------|----------|-------|----------|--------|
| GQ-01 | work_days — normal | order=Jun1, submit=Jun6 | Returns `5` | ✅ |
| GQ-02 | work_days — min 1 | order=submit (same day) | Returns `1` (not 0) | ✅ |
| GQ-03 | work_days — no submit | No submit_date set | Returns `None` | ✅ |
| GQ-04 | status_bg_style — wait | STATUS_WAIT | Contains `#475569` (slate) | ✅ |
| GQ-05 | status_bg_style — done | STATUS_DONE | Contains `#065f46` (emerald) | ✅ |
| GQ-06 | urgency_style — urgent | URGENCY_URGENT | Contains `#e11d48` (red) | ✅ |
| GQ-07 | urgency_style — normal | URGENCY_NORMAL | Does not contain `#e11d48` | ✅ |

### View Tests

| Case ID | Scenario | Steps | Expected | Result |
|---------|----------|-------|----------|--------|
| GQ-08 | queue_list 200 | GET `/graphicqueue/` | 200 OK | ✅ |
| GQ-09 | stat_cards in context | GET `/graphicqueue/` | `stat_cards` present | ✅ |
| GQ-10 | Backlog card = wait+prog | Create 1 wait + 1 prog + 1 done | `งานที่ค้าง` card count = 2 | ✅ |
| GQ-11 | table partial 200 | GET `/graphicqueue/htmx/rows/` | 200 OK | ✅ |
| GQ-12 | status filter | GET `?status=รอดำเนินการ` | Only waiting jobs | ✅ |
| GQ-13 | backlog filter excludes done | GET `?status=งานที่ค้าง` | Done job excluded | ✅ |
| GQ-14 | product_type filter | GET `?product_type=สินค้าเทส` | Only test-type jobs | ✅ |
| GQ-15 | assignee filter | GET `?assignee=มอส` | Only jobs for มอส | ✅ |
| GQ-16 | month filter | GET `?month=2025-06` | Only June orders | ✅ |
| GQ-17 | search filter | GET `?q=GQT02` | Only GQT02 | ✅ |
| GQ-18 | queue_add GET | GET `/graphicqueue/add/` | 200 OK modal | ✅ |
| GQ-19 | queue_add POST — with media | POST form with `media_type_ids` | Job created + 2 media types linked | ✅ |
| GQ-20 | queue_add POST — ref images with briefs | POST with 2 images + 2 briefs | 2 RefImage records; brief[0]="Brief A", brief[1]="Brief B" | ✅ |
| GQ-21 | queue_edit GET | GET `/<pk>/edit/` | 200 OK | ✅ |
| GQ-22 | queue_edit POST — update | POST updated name + status | DB record updated | ✅ |
| GQ-23 | queue_edit POST — delete ref | POST with `delete_ref_ids` | RefImage removed | ✅ |
| GQ-24 | queue_delete | POST to delete URL | Job removed from DB | ✅ |
| GQ-25 | media_type_add — new type | POST `new_type_name="New Video Type"` | MediaType created in DB | ✅ |
| GQ-26 | media_type_add — new type checked | Same as above | New type appears checked in HTML response | ✅ |
| GQ-27 | media_type_add — duplicate | POST same name twice | Only 1 record (get_or_create) | ✅ |
| GQ-28 | media_type_add — preserves checked | POST with existing `media_type_ids` | Existing IDs still checked in response | ✅ |
| GQ-29 | view_media_modal | GET `/<pk>/media/` | 200 OK; `video_media` contains 1 type | ✅ |
| GQ-30 | view_ref_modal | GET `/<pk>/ref/` | 200 OK; refs list has 1 RefImage with correct brief | ✅ |

### Seed / Form Tests

| Case ID | Scenario | Steps | Expected | Result |
|---------|----------|-------|----------|--------|
| GQ-31 | seed_graphicqueue — 10 types | Run `seed_graphicqueue` | 10 total (5 video + 5 image) | ✅ |
| GQ-32 | seed_graphicqueue — idempotent | Run `seed_graphicqueue` twice | Still 10 total, no duplicates | ✅ |
| GQ-33 | GraphicJobForm assignee queryset | Instantiate form | Queryset contains only `is_graphic=True, is_active=True` employees | ✅ |

---

## Summary

| System | Tests | Passed | Failed |
|--------|-------|--------|--------|
| Core / Auth | 28 | 28 | 0 |
| Phase 1 — Product Test | 33 | 33 | 0 |
| Phase 2 — Clearance | 28 | 28 | 0 |
| Phase 3 — Graphic Queue | 33 | 33 | 0 |
| **Total** | **122** | **122** | **0** |
