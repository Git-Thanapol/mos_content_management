# Changelog

All notable changes to MOS CMS are documented here.

---

## [2026-06-18]

### Phase 3 — Graphic Queue Center

#### ✨ New Features
- **Media quantities per type** — each media type in the add/edit form now has a `จำนวน [n] ชุด` input. Quantities are stored in `GraphicJob.media_quantities` (JSONField). Displayed as badges in the view-media modal.
- **New media type catalog** (re-seeded via `seed_graphicqueue --flush`):
  - งานคลิป (6): คลิป 1:1/4:5/9:16 × มีกรอบ/ไม่มีกรอบ
  - งานภาพ (3): ภาพ 1 ภาพ 4:5, ภาพ 1 ภาพ 9:16, ภาพ อัลบั้ม 4 ภาพ 1:1

#### 🐛 Bug Fixes
- **งานส่งล่าช้า**: fixed counting logic from `status ≠ เรียบร้อย` → `submit_date = null`, so any job past deadline without a submission date is counted as late (both stat card + filter).

#### 🎨 UI / UX
- **Stat cards**: คิวงานทั้งหมด = `#1890FF`; งานส่งล่าช้า = orange gradient with ring + pulse icon.
- **6-filter bar**: search, urgency, product type, assignee, date range (เริ่ม/สิ้นสุด).
- **Table column order**: เลือก (checkbox) first → จัดการ (edit) last; 16 columns total.
- **Deadline color coding**: overdue = red badge; ≤ 3 days = amber badge.
- **Media section headers**: red left-border for งานคลิป, blue left-border for งานภาพ.
- **Qty widget greyed out** when checkbox is unchecked (opacity 0.3 + pointer-events none); activates on check.
- **Custom thin scrollbar** (5 px) on table.
- **จำนวนวันที่ทำงาน** column shows `ยังไม่ส่งงาน` when submit_date is null.

#### 🔧 Technical
- Migration `0002_graphicjob_media_quantities` added.
- Template tag `get_qty` in `apps/graphicqueue/templatetags/graphicqueue_tags.py`.
- `seed_graphicqueue` now supports `--flush` flag to clear and re-seed media types.
- `media_type_add` HTMX endpoint preserves quantity values across DOM swap.

---

## [2026-06-17]

### Phase 2 — Clearance Products (ระบบสินค้าโล๊ะ)

#### ✨ New Features
- **วันที่ลงข้อมูล** field added to `ClearanceProduct` (DateField, default=today).
- **JST product images** displayed in the clearance table via `JST_BASE_URL` env var; graceful fallback icon when URL is unconfigured or image fails to load.

#### 🎨 UI / UX
- Add/edit modal reorganized to 3 rows × 2 cols:
  - Row 1: รหัสสินค้า | สถานะ
  - Row 2: ผู้รับผิดชอบ | วันที่ลงข้อมูล
  - Row 3: วันที่ดำเนินการ | วันที่เรียบร้อย

#### 🔧 Technical
- Migration `0002_clearanceproduct_date_added`.
- `JST_BASE_URL` added to `config/settings.py` and `.env.example`.
- `_build_image_url()` helper in `apps/clearance/jst.py` (fails safe to empty string).

---

### Phase 1 — Product Test System (ระบบสินค้า TEST)

#### 🐛 Bug Fixes
- **Date filters**: fixed `<tbody>` HTMX refresh not carrying date params; now uses `hx-include="#filter-form"`.
- **Supervisor date filters**: same fix applied; added `date_field` dropdown to filter by upload_date or start_date.
- **Commission form**: `STATUS_FAILED` (ไม่ผ่าน) excluded from user-facing dropdown; set automatically by view logic.

#### ✨ New Features
- **"ไม่ผ่าน" stat card** on supervisor page.
- **Auto-set commission to ไม่ผ่าน** when product status is `Test ไม่ผ่าน` or `ยกเลิก`; resets to รอกรอกค่าคอม when reverted.
- **ข้อมูลสินค้า / ข้อมูลสื่อ popup** (read-only) — replaces inline truncated text in the table.
- **Read-only price modal**: ราคาทดสอบ popup is now view + copy only; editing moved to the edit form.
- **Price editor in add/edit form**: dynamic rows with add/remove, serialized to `prices_json`.

#### 🎨 UI / UX
- Supervisor table: compact design — `py-2 px-2` padding, `.7rem` font for SKU/ชื่อสินค้า, 30×30 px thumbnails, 2-line wrapping headers.
- Manage button disabled when commission status = ไม่ผ่าน.

---
