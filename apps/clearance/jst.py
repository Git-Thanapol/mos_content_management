"""
JST service layer — batched reads, safe fallback when JST is unreachable.

All public functions return sensible defaults (empty dicts / empty lists)
if the JST database is down or a query fails — never raise to the caller.
"""
from __future__ import annotations

import logging
from typing import Sequence

logger = logging.getLogger(__name__)

_FALLBACK = {"name": "-", "stock": "-", "cost": "-", "last_order_date": None}


def _fallback_map(codes: Sequence[str]) -> dict:
    return {c: dict(_FALLBACK) for c in codes}


def search_products(q: str, limit: int = 20) -> list[dict]:
    """
    Search JST master items by product_code or name prefix/contains.
    Returns a list of {product_code, name} dicts. Empty list on error.
    """
    if not q or not q.strip():
        return []
    q = q.strip()
    try:
        from .jst_models import JstMasterItem
        from django.db.models import Q

        qs = (
            JstMasterItem.objects.using("jst")
            .filter(Q(product_code__icontains=q) | Q(name__icontains=q))
            .values("product_code", "name")[:limit]
        )
        return list(qs)
    except Exception as exc:
        logger.warning("JST search failed: %s", exc)
        return []


def enrich(codes: Sequence[str]) -> dict[str, dict]:
    """
    Given a list of JST product_codes, return a dict mapping each code to:
        {name, stock, cost, last_order_date}

    Runs 3 batched queries (names+stock subquery, PO items).
    Falls back to '-' / None for any code if JST is unreachable.
    """
    codes = [c for c in codes if c]
    if not codes:
        return {}

    result = _fallback_map(codes)

    try:
        from django.db.models import OuterRef, Subquery
        from .jst_models import JstMasterItem, JstStockSnapshot, JstPOItem

        # ── Query 1: name + latest stock snapshot (via subquery) ──────────────
        latest_qty_subq = (
            JstStockSnapshot.objects.using("jst")
            .filter(sku_id=OuterRef("pk"))
            .order_by("-snapshot_date", "-id")
            .values("quantity")[:1]
        )
        items = (
            JstMasterItem.objects.using("jst")
            .filter(product_code__in=codes)
            .annotate(latest_stock=Subquery(latest_qty_subq))
            .values("product_code", "name", "latest_stock")
        )
        for row in items:
            code = row["product_code"]
            result[code]["name"] = row["name"] or "-"
            stock = row["latest_stock"]
            result[code]["stock"] = stock if stock is not None else "-"

        # ── Query 2: latest PO item per code (order_date + landed cost) ──────
        # Fetch all PO items for these SKUs, ordered by header date desc.
        # Take the first (latest) per code in Python.
        all_po_items = (
            JstPOItem.objects.using("jst")
            .filter(sku__product_code__in=codes)
            .select_related("header")
            .order_by("-header__order_date", "-id")
            .values(
                "sku__product_code",
                "qty_ordered",
                "price_baht",
                "total_received_cbm",
                "header__order_date",
                "header__shipping_rate_thb_cbm",
            )
        )

        seen: set[str] = set()
        for item in all_po_items:
            code = item["sku__product_code"]
            if code in seen:
                continue
            seen.add(code)

            result[code]["last_order_date"] = item["header__order_date"]

            qty = item["qty_ordered"] or 1
            price_baht = float(item["price_baht"] or 0)
            cbm = float(item["total_received_cbm"] or 0)
            rate = float(item["header__shipping_rate_thb_cbm"] or 0)
            total_thb = price_baht + cbm * rate
            result[code]["cost"] = round(total_thb / qty, 2) if qty > 0 else 0

    except Exception as exc:
        logger.warning("JST enrich failed: %s", exc)
        # Return whatever was set before the error; defaults remain '-' / None

    return result
