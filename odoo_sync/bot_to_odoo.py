import logging
from config import ROOT_CATEGORY_NAME, WAREHOUSE_LOCATION_ID
import odoo_client as oc
import bot_db

logger = logging.getLogger(__name__)

def sync_categories():
    cat_map = {}
    root_id, _ = oc.create_or_update("product.category",
        [("name","=",ROOT_CATEGORY_NAME)], {"name": ROOT_CATEGORY_NAME})
    cat_map["__root__"] = root_id

    for cat in bot_db.get_all_categories():
        oid, st = oc.create_or_update("product.category",
            [("name","=",cat["name_uz"]),("parent_id","=",root_id)],
            {"name": cat["name_uz"], "parent_id": root_id})
        cat_map[cat["slug"]] = oid
        logger.debug(f"  {cat['slug']}: {st}")

    for sub in bot_db.get_all_subcategories():
        pid  = cat_map.get(sub["category_slug"], root_id)
        key  = f"{sub['category_slug']}/{sub['slug']}"
        oid, st = oc.create_or_update("product.category",
            [("name","=",sub["name_uz"]),("parent_id","=",pid)],
            {"name": sub["name_uz"], "parent_id": pid})
        cat_map[key] = oid

    logger.info(f"Kategoriyalar: {len(cat_map)} ta sync qilindi")
    return cat_map

def sync_products(cat_map):
    prod_map = {}; created = updated = 0
    for p in bot_db.get_all_products():
        key    = f"{p['category']}/{p['subcategory']}" if p["subcategory"] else None
        cat_id = cat_map.get(key) or cat_map.get(p["category"])
        desc   = " | ".join(filter(None,[p.get("format_size",""),p.get("thickness",""),p.get("location","")]))
        vals   = {"name":p["name"],"default_code":p["code"] or "","categ_id":cat_id,
                  "list_price":float(p.get("price") or 0),"standard_price":float(p.get("price") or 0),
                  "type":"product","description":desc,"active":True}
        domain = [("default_code","=",p["code"])] if p["code"] else [("name","=",p["name"])]
        oid, st = oc.create_or_update("product.template", domain, vals)
        prod_map[p["id"]] = oid
        if st=="created": created+=1
        else: updated+=1
    logger.info(f"Mahsulotlar: {created} yangi, {updated} yangilandi")
    return prod_map

def sync_stock(prod_map):
    count = 0
    for p in bot_db.get_all_products():
        tid = prod_map.get(p["id"])
        if not tid: continue
        var = oc.find_one("product.product",[("product_tmpl_id","=",tid)],fields=["id"])
        if not var: continue
        qty = float(p["quantity"] or 0)
        ex  = oc.find_one("stock.quant",
            [("product_id","=",var["id"]),("location_id","=",WAREHOUSE_LOCATION_ID)],
            fields=["id","quantity"])
        if ex:
            if abs(ex["quantity"]-qty)>0.001:
                oc.write("stock.quant",ex["id"],{"quantity":qty}); count+=1
        else:
            oc.create("stock.quant",{"product_id":var["id"],"location_id":WAREHOUSE_LOCATION_ID,"quantity":qty}); count+=1
    logger.info(f"Zaxira: {count} ta yangilandi")

def run():
    logger.info("Bot → Odoo sync boshlandi")
    if not oc.connect(): return False
    cat_map  = sync_categories()
    prod_map = sync_products(cat_map)
    sync_stock(prod_map)
    logger.info("Bot → Odoo sync tugadi ✅")
    return True
