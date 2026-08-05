# -*- coding: utf-8 -*-
"""
PostgreSQL versiyasi — Supabase / Render PostgreSQL bilan ishlaydi.
Barcha funksiyalar SQLite versiyasi bilan bir xil interfeys.
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import Optional, List, Dict, Any
import os

# DATABASE_URL = "postgresql://user:pass@host:5432/dbname"
DATABASE_URL = os.environ.get("DATABASE_URL", "")


def get_conn():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn


def init_db():
    conn = get_conn(); c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id   BIGINT PRIMARY KEY,
            language  TEXT DEFAULT 'uz',
            role      TEXT DEFAULT NULL,
            username  TEXT,
            full_name TEXT
        );
        CREATE TABLE IF NOT EXISTS categories (
            id         SERIAL PRIMARY KEY,
            slug       TEXT UNIQUE NOT NULL,
            name_uz    TEXT NOT NULL,
            name_ru    TEXT NOT NULL,
            name_en    TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS subcategories (
            id             SERIAL PRIMARY KEY,
            category_slug  TEXT NOT NULL,
            slug           TEXT NOT NULL,
            name_uz        TEXT NOT NULL,
            name_ru        TEXT NOT NULL,
            name_en        TEXT NOT NULL,
            UNIQUE(category_slug, slug)
        );
        CREATE TABLE IF NOT EXISTS products (
            id           SERIAL PRIMARY KEY,
            name         TEXT NOT NULL,
            code         TEXT,
            category     TEXT NOT NULL,
            subcategory  TEXT,
            format_size  TEXT,
            thickness    TEXT,
            quantity     REAL DEFAULT 0,
            min_quantity REAL DEFAULT 0,
            price        REAL DEFAULT 0,
            location     TEXT,
            image_path   TEXT,
            added_at     TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS movements (
            id            SERIAL PRIMARY KEY,
            product_id    INTEGER NOT NULL,
            movement_type TEXT NOT NULL,
            quantity      REAL NOT NULL,
            note          TEXT,
            admin_id      BIGINT NOT NULL,
            admin_name    TEXT,
            created_at    TEXT NOT NULL
        );
    """)
    conn.commit()
    from config import DEFAULT_CATEGORIES, DEFAULT_SUBCATEGORIES
    _seed_defaults(c, conn, DEFAULT_CATEGORIES, DEFAULT_SUBCATEGORIES)
    conn.close()


def _seed_defaults(c, conn, cats, subs):
    for slug, uz, ru, en in cats:
        c.execute("SELECT id FROM categories WHERE slug=%s", (slug,))
        if not c.fetchone():
            c.execute("INSERT INTO categories(slug,name_uz,name_ru,name_en,created_at) VALUES(%s,%s,%s,%s,%s)",
                      (slug, uz, ru, en, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    for cs, slug, uz, ru, en in subs:
        c.execute("SELECT id FROM subcategories WHERE category_slug=%s AND slug=%s", (cs, slug))
        if not c.fetchone():
            c.execute("INSERT INTO subcategories(category_slug,slug,name_uz,name_ru,name_en) VALUES(%s,%s,%s,%s,%s)",
                      (cs, slug, uz, ru, en))
    conn.commit()


# ─── USERS ───────────────────────────────────────────────────────────────────
def upsert_user(user_id, username=None, full_name=None):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE user_id=%s", (user_id,))
    if c.fetchone():
        c.execute("UPDATE users SET username=%s,full_name=%s WHERE user_id=%s",
                  (username, full_name, user_id))
    else:
        c.execute("INSERT INTO users(user_id,language,username,full_name) VALUES(%s,'uz',%s,%s)",
                  (user_id, username, full_name))
    conn.commit(); conn.close()

def get_user_lang(user_id):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT language FROM users WHERE user_id=%s", (user_id,))
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO users(user_id,language) VALUES(%s,'uz')", (user_id,))
        conn.commit(); conn.close(); return "uz"
    conn.close(); return row["language"]

def set_user_lang(user_id, lang):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE user_id=%s", (user_id,))
    if c.fetchone(): c.execute("UPDATE users SET language=%s WHERE user_id=%s", (lang, user_id))
    else:            c.execute("INSERT INTO users(user_id,language) VALUES(%s,%s)", (user_id, lang))
    conn.commit(); conn.close()

def user_has_language(user_id):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE user_id=%s", (user_id,))
    row = c.fetchone(); conn.close(); return row is not None

def get_user_role(user_id):
    from config import ADMIN_IDS, ROLE_SUPERADMIN
    if user_id in ADMIN_IDS: return ROLE_SUPERADMIN
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT role FROM users WHERE user_id=%s", (user_id,))
    row = c.fetchone(); conn.close()
    return row["role"] if row else None

def set_user_role(user_id, role):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE user_id=%s", (user_id,))
    if c.fetchone(): c.execute("UPDATE users SET role=%s WHERE user_id=%s", (role, user_id))
    else:            c.execute("INSERT INTO users(user_id,role) VALUES(%s,%s)", (user_id, role))
    conn.commit(); conn.close()

def get_admin_users():
    from config import ROLE_SUPERADMIN, ROLE_ADMIN
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM users WHERE role IN (%s,%s) ORDER BY user_id",
              (ROLE_SUPERADMIN, ROLE_ADMIN))
    rows = c.fetchall(); conn.close(); return rows

def get_all_notifiable_admin_ids():
    from config import ADMIN_IDS, ROLE_SUPERADMIN, ROLE_ADMIN
    ids = set(ADMIN_IDS)
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE role IN (%s,%s)", (ROLE_SUPERADMIN, ROLE_ADMIN))
    for r in c.fetchall(): ids.add(r["user_id"])
    conn.close(); return list(ids)


# ─── CATEGORIES ──────────────────────────────────────────────────────────────
def get_all_categories():
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM categories ORDER BY id")
    rows = c.fetchall(); conn.close(); return rows

def get_category(slug):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM categories WHERE slug=%s", (slug,))
    row = c.fetchone(); conn.close(); return row

def category_exists(slug): return get_category(slug) is not None

def add_category(slug, uz, ru, en):
    conn = get_conn(); c = conn.cursor()
    c.execute("INSERT INTO categories(slug,name_uz,name_ru,name_en,created_at) VALUES(%s,%s,%s,%s,%s) RETURNING id",
              (slug, uz, ru, en, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    nid = c.fetchone()["id"]; conn.commit(); conn.close(); return nid

def delete_category(slug):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT COUNT(*) as n FROM products WHERE category=%s", (slug,))
    if c.fetchone()["n"] > 0: conn.close(); return False
    c.execute("DELETE FROM subcategories WHERE category_slug=%s", (slug,))
    c.execute("DELETE FROM categories WHERE slug=%s", (slug,))
    conn.commit(); conn.close(); return True

def count_products_in_category(slug):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT COUNT(*) as n FROM products WHERE category=%s", (slug,))
    n = c.fetchone()["n"]; conn.close(); return n

def get_category_label(lang, slug):
    cat = get_category(slug)
    return cat[f"name_{lang}"] or cat["name_uz"] if cat else slug


# ─── SUBCATEGORIES ────────────────────────────────────────────────────────────
def get_subcategories(cat_slug):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM subcategories WHERE category_slug=%s ORDER BY id", (cat_slug,))
    rows = c.fetchall(); conn.close(); return rows

def get_subcategory(cat_slug, slug):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM subcategories WHERE category_slug=%s AND slug=%s", (cat_slug, slug))
    row = c.fetchone(); conn.close(); return row

def add_subcategory(cat_slug, slug, uz, ru, en):
    conn = get_conn(); c = conn.cursor()
    c.execute("INSERT INTO subcategories(category_slug,slug,name_uz,name_ru,name_en) VALUES(%s,%s,%s,%s,%s) RETURNING id",
              (cat_slug, slug, uz, ru, en))
    nid = c.fetchone()["id"]; conn.commit(); conn.close(); return nid

def delete_subcategory(cat_slug, slug):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT COUNT(*) as n FROM products WHERE category=%s AND subcategory=%s", (cat_slug, slug))
    if c.fetchone()["n"] > 0: conn.close(); return False
    c.execute("DELETE FROM subcategories WHERE category_slug=%s AND slug=%s", (cat_slug, slug))
    conn.commit(); conn.close(); return True

def count_products_in_subcategory(cat_slug, slug):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT COUNT(*) as n FROM products WHERE category=%s AND subcategory=%s", (cat_slug, slug))
    n = c.fetchone()["n"]; conn.close(); return n

def get_subcategory_label(lang, cat_slug, sub_slug):
    if not sub_slug: return "-"
    sub = get_subcategory(cat_slug, sub_slug)
    return sub[f"name_{lang}"] or sub["name_uz"] if sub else sub_slug

def get_distinct_subcategories(cat_slug):
    return [r["slug"] for r in get_subcategories(cat_slug)]


# ─── PRODUCTS ─────────────────────────────────────────────────────────────────
def add_product(name, code, category, subcategory, format_size,
                thickness, quantity, location, image_path=None, min_quantity=0, price=0):
    conn = get_conn(); c = conn.cursor()
    c.execute("""
        INSERT INTO products(name,code,category,subcategory,format_size,
                             thickness,quantity,min_quantity,price,location,image_path,added_at)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
    """, (name, code, category.lower().strip(),
          (subcategory or "").lower().strip() or None,
          format_size, thickness, quantity, min_quantity, price, location, image_path,
          datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    nid = c.fetchone()["id"]; conn.commit(); conn.close(); return nid

def get_product(pid):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM products WHERE id=%s", (pid,))
    row = c.fetchone(); conn.close(); return row

def get_product_by_code(code):
    if not code: return None
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM products WHERE code=%s", (code,))
    row = c.fetchone(); conn.close(); return row

def get_products_by_ids(ids):
    if not ids: return []
    conn = get_conn(); c = conn.cursor()
    c.execute(f"SELECT * FROM products WHERE id = ANY(%s)", (list(ids),))
    rows = c.fetchall(); conn.close()
    by_id = {r["id"]: r for r in rows}
    return [by_id[i] for i in ids if i in by_id]

def update_product_quantity(pid, new_qty):
    conn = get_conn(); c = conn.cursor()
    c.execute("UPDATE products SET quantity=%s WHERE id=%s", (new_qty, pid))
    conn.commit(); conn.close()

def set_min_quantity(pid, min_qty):
    conn = get_conn(); c = conn.cursor()
    c.execute("UPDATE products SET min_quantity=%s WHERE id=%s", (min_qty, pid))
    conn.commit(); conn.close()

def upsert_product(name, code, category, subcategory, format_size,
                   thickness, quantity, location, image_path=None, min_quantity=0, price=0):
    if code:
        existing = get_product_by_code(code)
        if existing:
            conn = get_conn(); c = conn.cursor()
            new_qty = existing["quantity"] + quantity
            c.execute("""UPDATE products SET name=%s,subcategory=%s,format_size=%s,
                         thickness=%s,quantity=%s,price=%s,location=%s WHERE code=%s""",
                      (name,(subcategory or "").lower().strip() or None,
                       format_size,thickness,new_qty,price,location,code))
            conn.commit(); pid = existing["id"]; conn.close()
            return pid, "updated"
    pid = add_product(name,code,category,subcategory,format_size,
                      thickness,quantity,location,image_path,min_quantity,price)
    return pid, "added"

def delete_product_by_code(code):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM products WHERE code=%s", (code,))
    row = c.fetchone()
    if not row: conn.close(); return None
    c.execute("DELETE FROM products WHERE code=%s", (code,))
    conn.commit(); conn.close(); return row

def delete_product_by_id(pid):
    conn = get_conn(); c = conn.cursor()
    c.execute("DELETE FROM products WHERE id=%s", (pid,))
    ok = c.rowcount > 0; conn.commit(); conn.close(); return ok

def get_products_by_category(category, subcategory=None):
    conn = get_conn(); c = conn.cursor()
    if subcategory:
        c.execute("SELECT * FROM products WHERE category=%s AND subcategory=%s ORDER BY id DESC",
                  (category.lower(), subcategory.lower()))
    else:
        c.execute("SELECT * FROM products WHERE category=%s ORDER BY id DESC", (category.lower(),))
    rows = c.fetchall(); conn.close(); return rows

def get_all_products():
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM products ORDER BY id DESC")
    rows = c.fetchall(); conn.close(); return rows

def get_low_stock_products():
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM products WHERE min_quantity>0 AND quantity<min_quantity ORDER BY quantity ASC")
    rows = c.fetchall(); conn.close(); return rows

def _search(field, q):
    conn = get_conn(); c = conn.cursor()
    c.execute(f"SELECT * FROM products WHERE {field} ILIKE %s ORDER BY id DESC", (f"%{q}%",))
    rows = c.fetchall(); conn.close(); return rows

def search_by_name(q):     return _search("name", q)
def search_by_code(q):     return _search("code", q)
def search_by_format(q):   return _search("format_size", q)
def search_by_thickness(q):return _search("thickness", q)

def search_kromka_by_format(fmt):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM products WHERE category='kromka' AND (subcategory ILIKE %s OR format_size ILIKE %s) ORDER BY id DESC",
              (f"%{fmt}%", f"%{fmt}%"))
    rows = c.fetchall(); conn.close(); return rows


# ─── MOVEMENTS ────────────────────────────────────────────────────────────────
def record_movement(product_id, mv_type, qty, note, admin_id, admin_name):
    conn = get_conn(); c = conn.cursor()
    c.execute("""INSERT INTO movements(product_id,movement_type,quantity,note,admin_id,admin_name,created_at)
                 VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
              (product_id, mv_type, qty, note or "", admin_id, admin_name or "",
               datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    nid = c.fetchone()["id"]; conn.commit(); conn.close(); return nid

def get_product_movements(pid, limit=20):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM movements WHERE product_id=%s ORDER BY id DESC LIMIT %s", (pid, limit))
    rows = c.fetchall(); conn.close(); return rows


# ─── STATISTIKA ───────────────────────────────────────────────────────────────
def get_stats():
    conn = get_conn(); c = conn.cursor()
    now   = datetime.now()
    today = now.strftime("%Y-%m-%d")
    month = now.strftime("%Y-%m")

    def cnt(sql, *args):
        c.execute(sql, args); r = c.fetchone()
        return list(r.values())[0] if r else 0

    def mv(mv_type, period):
        if period == "today":
            c.execute("SELECT COALESCE(SUM(quantity),0) FROM movements WHERE movement_type=%s AND created_at::date=%s::date",
                      (mv_type, today))
        else:
            c.execute("SELECT COALESCE(SUM(quantity),0) FROM movements WHERE movement_type=%s AND TO_CHAR(created_at::date,'YYYY-MM')=%s",
                      (mv_type, month))
        r = c.fetchone(); return list(r.values())[0] if r else 0

    s = {
        "total_products":   cnt("SELECT COUNT(*) FROM products"),
        "total_categories": cnt("SELECT COUNT(*) FROM categories"),
        "low_stock_count":  cnt("SELECT COUNT(*) FROM products WHERE min_quantity>0 AND quantity<min_quantity"),
        "added_today":      cnt("SELECT COUNT(*) FROM products WHERE added_at::date=%s::date", today),
        "added_month":      cnt("SELECT COUNT(*) FROM products WHERE TO_CHAR(added_at::date,'YYYY-MM')=%s", month),
        "in_today":  mv("IN","today"),  "out_today":  mv("OUT","today"),
        "in_month":  mv("IN","month"),  "out_month":  mv("OUT","month"),
    }
    conn.close(); return s


# ─── TARIX ────────────────────────────────────────────────────────────────────
def get_active_days(limit=90):
    conn = get_conn(); c = conn.cursor()
    c.execute("""
        SELECT day, SUM(cnt) as total FROM (
            SELECT DATE(added_at) as day, COUNT(*) as cnt FROM products GROUP BY DATE(added_at)
            UNION ALL
            SELECT DATE(created_at) as day, COUNT(*) as cnt FROM movements GROUP BY DATE(created_at)
        ) t GROUP BY day ORDER BY day DESC LIMIT %s
    """, (limit,))
    rows = c.fetchall(); conn.close()
    return [{"day": str(r["day"]), "total": r["total"]} for r in rows]

def get_day_detail(date_str):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM products WHERE added_at::date=%s::date ORDER BY added_at", (date_str,))
    products = c.fetchall()
    c.execute("""SELECT m.*,p.name as prod_name,p.code as prod_code
                 FROM movements m LEFT JOIN products p ON m.product_id=p.id
                 WHERE m.created_at::date=%s::date ORDER BY m.created_at""", (date_str,))
    movements = c.fetchall(); conn.close()
    return products, movements

def get_day_summary(date_str):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT COUNT(*) as n FROM products WHERE added_at::date=%s::date", (date_str,))
    added = c.fetchone()["n"]
    c.execute("""SELECT movement_type, COUNT(*) as cnt, COALESCE(SUM(quantity),0) as total
                 FROM movements WHERE created_at::date=%s::date GROUP BY movement_type""", (date_str,))
    mv = {r["movement_type"]: {"cnt":r["cnt"],"total":r["total"]} for r in c.fetchall()}
    conn.close()
    return {"added":added,
            "in_cnt":mv.get("IN",{}).get("cnt",0),"in_total":mv.get("IN",{}).get("total",0),
            "out_cnt":mv.get("OUT",{}).get("cnt",0),"out_total":mv.get("OUT",{}).get("total",0)}

def row_to_dict(row):
    if isinstance(row, dict): return row
    return dict(row)
