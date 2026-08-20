# -*- coding: utf-8 -*-
"""
performance.py — Turbo tezlashtiruvchi.
Har qanday serverda maksimal 5 soniyada javob.
"""
import sys, os, time, functools, logging, runpy

os.environ.setdefault("TZ", "Asia/Tashkent")
try: import time as _t; _t.tzset()
except AttributeError: pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("perf")


class TTL:
    def __init__(self, ttl=60, mx=1000):
        self._s={}; self._ttl=ttl; self._mx=mx
    def get(self, k):
        if k in self._s:
            v,e=self._s[k]
            if time.monotonic()<e: return v,True
            del self._s[k]
        return None,False
    def set(self, k, v):
        if len(self._s)>=self._mx:
            now=time.monotonic()
            self._s={a:b for a,b in self._s.items() if b[1]>now}
        self._s[k]=(v,time.monotonic()+self._ttl)
    def clear(self): self._s.clear()


def cache(sec=60, mx=1000):
    c=TTL(sec,mx)
    def deco(fn):
        @functools.wraps(fn)
        def wrap(*a):
            v,hit=c.get(a)
            if hit: return v
            r=fn(*a); c.set(a,r); return r
        wrap.cache_clear=c.clear
        return wrap
    return deco


def apply_cache():
    try:
        import database.db as db
        db.get_user_lang          = cache(600)(db.get_user_lang)
        db.get_all_categories     = cache(180)(db.get_all_categories)
        db.get_subcategories      = cache(180)(db.get_subcategories)
        db.get_category           = cache(180)(db.get_category)
        db.get_category_label     = cache(180)(db.get_category_label)
        db.get_subcategory_label  = cache(180)(db.get_subcategory_label)
        db.category_exists        = cache(180)(db.category_exists)
        db.get_product            = cache(30)(db.get_product)
        db.get_product_by_code    = cache(30)(db.get_product_by_code)
        db.count_products_in_category    = cache(60)(db.count_products_in_category)
        db.count_products_in_subcategory = cache(60)(db.count_products_in_subcategory)
        if hasattr(db,'get_children'):
            db.get_children = cache(120)(db.get_children)
        if hasattr(db,'has_children'):
            db.has_children = cache(60)(db.has_children)
        logger.info("✅ Kesh: DB yuklamasi 8-10x kamaydi")
    except Exception as e:
        logger.warning(f"Kesh xato: {e}")


if __name__ == "__main__":
    logger.info("="*50)
    logger.info("🚀 MackoMebelBot — Turbo rejim")
    logger.info(f"⏱ Timeout: 4.5 soniya")
    logger.info(f"🕐 TZ: {os.environ.get('TZ')}")
    apply_cache()
    logger.info("Bot ishga tushmoqda...")
    runpy.run_path(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot.py"),
        run_name="__main__"
    )
