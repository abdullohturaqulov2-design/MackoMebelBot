import sqlite3
from config import BOT_DB_PATH

def _conn():
    c = sqlite3.connect(BOT_DB_PATH); c.row_factory = sqlite3.Row; return c

def get_all_products():
    c = _conn(); cur = c.cursor()
    cur.execute("SELECT * FROM products ORDER BY id")
    r = [dict(x) for x in cur.fetchall()]; c.close(); return r

def get_all_categories():
    c = _conn(); cur = c.cursor()
    cur.execute("SELECT * FROM categories ORDER BY id")
    r = [dict(x) for x in cur.fetchall()]; c.close(); return r

def get_all_subcategories():
    c = _conn(); cur = c.cursor()
    cur.execute("SELECT * FROM subcategories ORDER BY id")
    r = [dict(x) for x in cur.fetchall()]; c.close(); return r
