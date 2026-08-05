# -*- coding: utf-8 -*-
"""
performance.py — Bot kesh tezlashtiruvchi.
bot.py yoniga qo'ying. render.yaml da:
  startCommand: python performance.py

MUHIM: HTTP server OCHILMAYDI — bot.py o'zi ochadi (port conflict yo'q)
"""
import sys, os, time, functools, logging, runpy

# Toshkent vaqti
os.environ.setdefault("TZ", "Asia/Tashkent")
try:
    import time as _t; _t.tzset()
except AttributeError:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("performance")


def ttl_cache(seconds=60):
    def deco(fn):
        _store = {}
        @functools.wraps(fn)
        def wrapper(*args):
            now = time.monotonic()
            if args in _store and now - _store[args][1] < seconds:
                return _store[args][0]
            result = fn(*args)
            _store[args] = (result, now)
            return result
        wrapper.cache_clear = lambda: _store.clear()
        return wrapper
    return deco


def apply_cache():
    try:
        import database.db as db
        db.get_user_lang          = ttl_cache(300)(db.get_user_lang)
        db.get_all_categories     = ttl_cache(120)(db.get_all_categories)
        db.get_subcategories      = ttl_cache(120)(db.get_subcategories)
        db.get_category           = ttl_cache(120)(db.get_category)
        db.get_category_label     = ttl_cache(120)(db.get_category_label)
        db.get_subcategory_label  = ttl_cache(120)(db.get_subcategory_label)
        db.category_exists        = ttl_cache(120)(db.category_exists)
        db.get_product            = ttl_cache(30)(db.get_product)
        db.count_products_in_category    = ttl_cache(60)(db.count_products_in_category)
        db.count_products_in_subcategory = ttl_cache(60)(db.count_products_in_subcategory)
        logger.info("✅ Kesh qo'llanildi — DB yuklamasi kamaydi")
    except Exception as e:
        logger.warning(f"Kesh qo'llanmadi: {e}")


if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("MackoMebelBot (tezlashtirilgan) ishga tushmoqda...")
    logger.info(f"Vaqt zonasi: {os.environ.get('TZ','default')}")
    apply_cache()
    logger.info("Bot ishga tushmoqda...")
    logger.info("=" * 50)
    runpy.run_path(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot.py"),
        run_name="__main__"
    )
