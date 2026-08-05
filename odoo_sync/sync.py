# -*- coding: utf-8 -*-
"""
Bot SQLite → Odoo sinxronizatsiya.

Tartib:
  1. Kategoriyalar sinxronlanadi
  2. Mahsulotlar sinxronlanadi (qo'shish/yangilash)
  3. Zaxira miqdorlari yangilanadi
"""
import logging
from config import ROOT_CATEGORY_NAME, WAREHOUSE_LOCATION_ID
import odoo_client as oc
import bot_db

logger = logging.getLogger(__name__)


# ─── 1. KATEGORIYALAR ─────────────────────────────────────────────────────────

def sync_categories():
    """
    Bot kategoriyalarini Odoo product.category ga sinxronlaydi.
    Qaytaradi: {bot_slug: odoo_category_id}
    """
    logger.info("Kategoriyalar sinxronlanmoqda...")
    cat_map = {}   # {slug: odoo_id}

    # Asosiy (root) kategoriyani topish yoki yaratish
    root_id, _ = oc.create_or_update(
        "product.category",
        [("name", "=", ROOT_CATEGORY_NAME)],
        {"name": ROOT_CATEGORY_NAME}
    )
    cat_map["__root__"] = root_id

    # Bot kategoriyalari
    for cat in bot_db.get_all_categories():
        name     = cat["name_uz"]   # o'zbek nomi
        slug     = cat["slug"]
        odoo_id, status = oc.create_or_update(
            "product.category",
            [("name", "=", name), ("parent_id", "=", root_id)],
            {"name": name, "parent_id": root_id}
        )
        cat_map[slug] = odoo_id
        logger.debug(f"  Kategoriya {slug}: {status} (id={odoo_id})")

    # Subkategoriyalar
    for sub in bot_db.get_all_subcategories():
        parent_id = cat_map.get(sub["category_slug"], root_id)
        name      = sub["name_uz"]
        sub_key   = f"{sub['category_slug']}/{sub['slug']}"
        odoo_id, status = oc.create_or_update(
            "product.category",
            [("name", "=", name), ("parent_id", "=", parent_id)],
            {"name": name, "parent_id": parent_id}
        )
        cat_map[sub_key] = odoo_id
        logger.debug(f"  Subkategoriya {sub_key}: {status} (id={odoo_id})")

    logger.info(f"Kategoriyalar: {len(cat_map)} ta sinxronlandi")
    return cat_map


# ─── 2. MAHSULOTLAR ───────────────────────────────────────────────────────────

def sync_products(cat_map):
    """
    Bot mahsulotlarini Odoo product.template ga sinxronlaydi.
    Qaytaradi: {bot_product_id: odoo_product_id}
    """
    logger.info("Mahsulotlar sinxronlanmoqda...")
    prod_map = {}
    products = bot_db.get_all_products()
    created = updated = 0

    for p in products:
        # Kategoriya ID ni topish
        sub_key = f"{p['category']}/{p['subcategory']}" if p["subcategory"] else None
        cat_id  = cat_map.get(sub_key) or cat_map.get(p["category"])

        # Mahsulot tavsifi
        desc_parts = []
        if p["format_size"]:   desc_parts.append(f"Format: {p['format_size']}")
        if p["thickness"]:     desc_parts.append(f"Qalinlik: {p['thickness']}")
        if p["location"]:      desc_parts.append(f"Joy: {p['location']}")
        description = " | ".join(desc_parts)

        vals = {
            "name":           p["name"],
            "default_code":   p["code"] or "",      # internal reference
            "categ_id":       cat_id,
            "list_price":     float(p.get("price") or 0),
            "standard_price": float(p.get("price") or 0),
            "type":           "product",             # storable
            "description":    description,
            "active":         True,
        }

        # Kod bo'yicha topish (kod bo'lmasa nom bo'yicha)
        domain = ([("default_code", "=", p["code"])] if p["code"]
                  else [("name", "=", p["name"])])

        odoo_id, status = oc.create_or_update("product.template", domain, vals)
        prod_map[p["id"]] = odoo_id
        if status == "created": created += 1
        else:                   updated += 1

    logger.info(f"Mahsulotlar: {created} ta yangi, {updated} ta yangilandi")
    return prod_map


# ─── 3. ZAXIRA MIQDORLARI ─────────────────────────────────────────────────────

def sync_stock(prod_map):
    """
    Bot mahsulotlari miqdorlarini Odoo zaxirasiga sinxronlaydi.
    stock.quant orqali inventory adjustment qiladi.
    """
    logger.info("Zaxira miqdorlari sinxronlanmoqda...")
    products = bot_db.get_all_products()
    count    = 0

    for p in products:
        template_id = prod_map.get(p["id"])
        if not template_id: continue

        # product.template → product.product (variant) ID ni topish
        variant = oc.find_one(
            "product.product",
            [("product_tmpl_id", "=", template_id)],
            fields=["id"]
        )
        if not variant: continue
        variant_id = variant["id"]
        qty        = float(p["quantity"] or 0)

        # Mavjud stock.quant ni topish
        existing = oc.find_one(
            "stock.quant",
            [("product_id", "=", variant_id),
             ("location_id", "=", WAREHOUSE_LOCATION_ID)],
            fields=["id", "quantity"]
        )

        if existing:
            # Faqat farq bo'lsa yangilash
            if abs(existing["quantity"] - qty) > 0.001:
                oc.write("stock.quant", existing["id"], {"quantity": qty})
                count += 1
        else:
            oc.create("stock.quant", {
                "product_id":  variant_id,
                "location_id": WAREHOUSE_LOCATION_ID,
                "quantity":    qty,
            })
            count += 1

    logger.info(f"Zaxira: {count} ta yangilandi")


# ─── ASOSIY FUNKSIYA ──────────────────────────────────────────────────────────

def run_sync():
    """To'liq sinxronizatsiyani ishga tushiradi."""
    logger.info("=" * 50)
    logger.info("Sinxronizatsiya boshlanmoqda...")

    if not oc.connect():
        logger.error("Odoo ga ulanib bo'lmadi. Sinxronizatsiya to'xtatildi.")
        return False

    cat_map  = sync_categories()
    prod_map = sync_products(cat_map)
    sync_stock(prod_map)

    logger.info("Sinxronizatsiya muvaffaqiyatli yakunlandi!")
    logger.info("=" * 50)
    return True
