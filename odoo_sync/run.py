"""
Ishga tushirish:
  python run.py              ← bir marta to'liq sync
  python run.py --daemon     ← har 5 daqiqada avtomatik
  python run.py --direction bot_to_odoo   ← faqat bot→odoo
  python run.py --direction odoo_to_bot   ← faqat odoo→bot
"""
import sys, time, logging
from config import SYNC_INTERVAL_MINUTES
import bot_to_odoo, odoo_to_bot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(),
              logging.FileHandler("sync.log", encoding="utf-8")]
)

def full_sync():
    bot_to_odoo.run()   # Bot → Odoo (mahsulotlar, kategoriyalar, zaxira)
    odoo_to_bot.run()   # Odoo → Bot (sotuvlar, miqdor kamayishi)

direction = None
for i, arg in enumerate(sys.argv):
    if arg == "--direction" and i+1 < len(sys.argv):
        direction = sys.argv[i+1]

if "--daemon" in sys.argv:
    print(f"Daemon: har {SYNC_INTERVAL_MINUTES} daqiqada sync")
    while True:
        try:
            if direction == "bot_to_odoo":  bot_to_odoo.run()
            elif direction == "odoo_to_bot": odoo_to_bot.run()
            else:                            full_sync()
        except Exception as e:
            logging.error(f"Sync xatosi: {e}")
        time.sleep(SYNC_INTERVAL_MINUTES * 60)
else:
    if direction == "bot_to_odoo":  bot_to_odoo.run()
    elif direction == "odoo_to_bot": odoo_to_bot.run()
    else:                            full_sync()
