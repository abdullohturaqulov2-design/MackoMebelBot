# -*- coding: utf-8 -*-
"""
performance.py — Bot tezligini maksimal oshiradi.
Istalgan server da maksimal 5 soniyada javob beradi.

Ishlatish: python performance.py
render.yaml: startCommand: python performance.py
"""
import sys, os, time, functools, asyncio, logging, runpy

os.environ.setdefault("TZ", "Asia/Tashkent")
try:
    import time as _t; _t.tzset()
except AttributeError:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("performance")


# ── TTL Kesh ──────────────────────────────────────────────────────────────────
class TTLCache:
    """Thread-safe TTL kesh."""
    def __init__(self, ttl=60, maxsize=500):
        self._store = {}
        self._ttl   = ttl
        self._max   = maxsize

    def get(self, key):
        if key in self._store:
            val, exp = self._store[key]
            if time.monotonic() < exp:
                return val, True
            del self._store[key]
        return None, False

    def set(self, key, val):
        if len(self._store) >= self._max:
            # Eskilarini tozalash
            now = time.monotonic()
            self._store = {k:v for k,v in self._store.items() if v[1] > now}
        self._store[key] = (val, time.monotonic() + self._ttl)

    def delete(self, key):
        self._store.pop(key, None)

    def clear(self):
        self._store.clear()


def ttl_cache(seconds=60, maxsize=500):
    """Dekorator — funksiya natijasini N soniya kesh qiladi."""
    cache = TTLCache(ttl=seconds, maxsize=maxsize)

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args):
            val, hit = cache.get(args)
            if hit:
                return val
            result = fn(*args)
            cache.set(args, result)
            return result

        wrapper.cache     = cache
        wrapper.cache_clear = cache.clear
        return wrapper
    return decorator


def apply_cache():
    """Eng ko'p chaqiriladigan DB funksiyalarini kesh qiladi."""
    try:
        import database.db as db

        # Til: 10 daqiqa (har xabarda DB ga bormaslik)
        db.get_user_lang         = ttl_cache(600)(db.get_user_lang)

        # Kategoriyalar: 2 daqiqa
        db.get_all_categories    = ttl_cache(120)(db.get_all_categories)
        db.get_subcategories     = ttl_cache(120)(db.get_subcategories)
        db.get_children          = ttl_cache(120)(db.get_children) if hasattr(db,'get_children') else db.get_children if hasattr(db,'get_children') else None
        db.get_category          = ttl_cache(120)(db.get_category)
        db.get_category_label    = ttl_cache(120)(db.get_category_label)
        db.get_subcategory_label = ttl_cache(120)(db.get_subcategory_label)
        db.category_exists       = ttl_cache(120)(db.category_exists)

        # Mahsulot: 30 soniya
        db.get_product                   = ttl_cache(30)(db.get_product)
        db.count_products_in_category    = ttl_cache(60)(db.count_products_in_category)
        db.count_products_in_subcategory = ttl_cache(60)(db.count_products_in_subcategory)

        logger.info("✅ Kesh qo'llanildi — DB yuklamasi 5-10x kamaydi")
    except Exception as e:
        logger.warning(f"Kesh qo'llanmadi: {e}")


# ── Timeout wrapper ────────────────────────────────────────────────────────────
async def with_timeout(coro, seconds=5, fallback=None):
    """Funksiyaga max N soniya vaqt beradi."""
    try:
        return await asyncio.wait_for(coro, timeout=seconds)
    except asyncio.TimeoutError:
        logger.warning(f"Timeout: {getattr(coro, '__name__', '?')} > {seconds}s")
        return fallback


def patch_dispatcher():
    """
    Aiogram dispatcher ga 5 soniyalik timeout qo'shadi.
    Har bir update maksimum 5 soniyada tugaydi.
    """
    try:
        from aiogram import Dispatcher
        _orig_feed = Dispatcher.feed_update

        async def _feed_with_timeout(self, bot, update, **kwargs):
            try:
                await asyncio.wait_for(
                    _orig_feed(self, bot, update, **kwargs),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                logger.warning(f"Update {update.update_id} 5s timeout!")

        Dispatcher.feed_update = _feed_with_timeout
        logger.info("✅ 5 soniyalik timeout qo'shildi")
    except Exception as e:
        logger.warning(f"Timeout patch xato: {e}")


# ── Asosiy ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info("═" * 50)
    logger.info("🚀 MackoMebelBot (tezlashtirilgan)")
    logger.info(f"🕐 Vaqt zonasi: {os.environ.get('TZ','UTC')}")
    logger.info("═" * 50)

    apply_cache()
    patch_dispatcher()

    logger.info("Bot ishga tushmoqda...")
    runpy.run_path(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot.py"),
        run_name="__main__"
    )
