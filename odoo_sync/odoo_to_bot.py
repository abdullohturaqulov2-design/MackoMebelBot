import sqlite3, logging, os
from datetime import datetime
from config import BOT_DB_PATH
import odoo_client as oc

logger     = logging.getLogger(__name__)
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_sync.txt")

def _last_sync():
    return open(STATE_FILE).read().strip() if os.path.exists(STATE_FILE) else "2000-01-01 00:00:00"

def _save_sync():
    with open(STATE_FILE,"w") as f: f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

def _bot_conn():
    c = sqlite3.connect(BOT_DB_PATH); c.row_factory = sqlite3.Row; return c

def _change_qty(code, delta, note):
    conn = _bot_conn(); c = conn.cursor()
    c.execute("SELECT id,quantity,name FROM products WHERE code=?",(code,))
    row = c.fetchone()
    if not row: conn.close(); return False
    new_qty = max(0, row["quantity"] + delta)
    c.execute("UPDATE products SET quantity=? WHERE id=?",(new_qty,row["id"]))
    mv_type = "OUT" if delta < 0 else "IN"
    c.execute("""INSERT INTO movements(product_id,movement_type,quantity,note,admin_id,admin_name,created_at)
                 VALUES(?,?,?,?,0,'Odoo',?)""",
              (row["id"], mv_type, abs(delta), note, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit(); conn.close()
    action = "➖" if delta < 0 else "➕"
    logger.info(f"  {action} {row['name']} ({code}): {delta:+.0f} → {new_qty}")
    return True

def run():
    last = _last_sync()
    logger.info(f"Odoo → Bot sync (oxirgi: {last})...")

    if not oc.connect(): return 0

    # Chiqimlar (sotuvlar, delivery)
    moves = oc.search("stock.move",[
        ("state","=","done"),
        ("picking_type_id.code","=","outgoing"),
        ("date",">",last),
    ], fields=["product_id","quantity_done","date","reference"])

    count = 0
    for m in moves:
        pid = m["product_id"][0] if m["product_id"] else None
        qty = float(m.get("quantity_done") or 0)
        if not pid or qty<=0: continue
        info = oc.find_one("product.product",[("id","=",pid)],fields=["default_code","name"])
        if not info: continue
        code = info.get("default_code","")
        if code and _change_qty(code, -qty, f"Odoo savdo: {m.get('reference','')}"): count+=1

    # Qaytarilganlar (return)
    returns = oc.search("stock.move",[
        ("state","=","done"),
        ("picking_type_id.code","=","incoming"),
        ("origin_returned_move_id","!=",False),
        ("date",">",last),
    ], fields=["product_id","quantity_done"])

    for m in returns:
        pid = m["product_id"][0] if m["product_id"] else None
        qty = float(m.get("quantity_done") or 0)
        if not pid or qty<=0: continue
        info = oc.find_one("product.product",[("id","=",pid)],fields=["default_code"])
        if info and info.get("default_code"):
            _change_qty(info["default_code"], qty, "Odoo qaytarildi")

    _save_sync()
    logger.info(f"Odoo → Bot: {count} ta chiqim bot bazasiga tushirildi ✅")
    return count
