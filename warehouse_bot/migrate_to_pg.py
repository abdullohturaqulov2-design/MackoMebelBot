#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite → PostgreSQL migration.
Bir marta ishga tushiriladi — eski ma'lumotlarni ko'chiradi.

Ishlatish:
  python migrate_to_pg.py
"""
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
import os, sys

SQLITE_PATH  = os.environ.get("SQLITE_PATH", "data/warehouse.db")
DATABASE_URL = os.environ.get("DATABASE_URL", "")

def migrate():
    if not DATABASE_URL:
        print("❌ DATABASE_URL yo'q! .env faylda belgilang.")
        sys.exit(1)
    if not os.path.exists(SQLITE_PATH):
        print(f"❌ SQLite fayl topilmadi: {SQLITE_PATH}")
        sys.exit(1)

    sq = sqlite3.connect(SQLITE_PATH); sq.row_factory = sqlite3.Row
    pg = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    sc = sq.cursor(); pc = pg.cursor()

    print("🔄 Migration boshlanmoqda...")

    # ── users ──────────────────────────────────────────────────────────────────
    sc.execute("SELECT * FROM users")
    users = sc.fetchall()
    for u in users:
        pc.execute("""
            INSERT INTO users(user_id,language,role,username,full_name)
            VALUES(%s,%s,%s,%s,%s) ON CONFLICT(user_id) DO NOTHING
        """, (u["user_id"],u["language"],u["role"] if "role" in u.keys() else None,
              u["username"] if "username" in u.keys() else None,
              u["full_name"] if "full_name" in u.keys() else None))
    print(f"  ✅ Users: {len(users)} ta")

    # ── categories ─────────────────────────────────────────────────────────────
    sc.execute("SELECT * FROM categories")
    cats = sc.fetchall()
    for c in cats:
        pc.execute("""
            INSERT INTO categories(slug,name_uz,name_ru,name_en,created_at)
            VALUES(%s,%s,%s,%s,%s) ON CONFLICT(slug) DO NOTHING
        """, (c["slug"],c["name_uz"],c["name_ru"],c["name_en"],c["created_at"]))
    print(f"  ✅ Categories: {len(cats)} ta")

    # ── subcategories ──────────────────────────────────────────────────────────
    sc.execute("SELECT * FROM subcategories")
    subs = sc.fetchall()
    for s in subs:
        pc.execute("""
            INSERT INTO subcategories(category_slug,slug,name_uz,name_ru,name_en)
            VALUES(%s,%s,%s,%s,%s) ON CONFLICT(category_slug,slug) DO NOTHING
        """, (s["category_slug"],s["slug"],s["name_uz"],s["name_ru"],s["name_en"]))
    print(f"  ✅ Subcategories: {len(subs)} ta")

    # ── products ───────────────────────────────────────────────────────────────
    sc.execute("SELECT * FROM products")
    prods = sc.fetchall()
    keys = [k for k in prods[0].keys()] if prods else []
    for p in prods:
        pc.execute("""
            INSERT INTO products(name,code,category,subcategory,format_size,
                                 thickness,quantity,min_quantity,price,location,image_path,added_at)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (p["name"],p["code"],p["category"],p["subcategory"],p["format_size"],
              p["thickness"],p["quantity"],
              p["min_quantity"] if "min_quantity" in keys else 0,
              p["price"] if "price" in keys else 0,
              p["location"],p["image_path"],p["added_at"]))
    print(f"  ✅ Products: {len(prods)} ta")

    # ── movements ──────────────────────────────────────────────────────────────
    sc.execute("SELECT * FROM movements")
    movs = sc.fetchall()
    for m in movs:
        pc.execute("""
            INSERT INTO movements(product_id,movement_type,quantity,note,admin_id,admin_name,created_at)
            VALUES(%s,%s,%s,%s,%s,%s,%s)
        """, (m["product_id"],m["movement_type"],m["quantity"],m["note"],
              m["admin_id"],m["admin_name"],m["created_at"]))
    print(f"  ✅ Movements: {len(movs)} ta")

    pg.commit(); sq.close(); pg.close()
    print("\n✅ Migration muvaffaqiyatli yakunlandi!")

if __name__ == "__main__":
    migrate()
