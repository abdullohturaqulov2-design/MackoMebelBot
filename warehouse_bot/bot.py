# -*- coding: utf-8 -*-
import asyncio
import logging
import os
import time
import json as _json
import urllib.request as _ur
import urllib.error as _ue

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from handlers import (start, language, menu, categories, admin_mgr,
                      add_products, delete_products, stats, movement,
                      warehouse, lists, search, photo_upload, history,
                      manual_add, manual_delete, scanner, qr_handler,
                      macko_ai_handler, excel_export)
from config import BOT_TOKEN, DATA_DIR
from database.db import init_db
from utils.image_utils import ensure_no_image_placeholder
from utils.qr_utils import init_qr_dir
from middlewares.auto_init import AutoInitMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

# ── Gemini AI ─────────────────────────────────────────────────────────────────
AI_SYSTEM = """Siz MackoMebelBot uchun Macko AI yordamchisisiz.
Mebel, plita, akril, MDF, XDF, laminat, kromka haqida maslahat beradi.
O'zbek, rus va ingliz tillarida gaplashadi. Qisqa va aniq javoblar beradi.
Iltimos hech qanday chuqur uylamangda max 15ta gap bilan foydalanuvchiga tushunarli javob bering """

ENDPOINTS = [
    "https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent",
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
    "https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent",
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
    "https://generativelanguage.googleapis.com/v1/models/gemini-2.5-pro:generateContent",
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent",
    "https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash-preview-tts:generateContent",
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent",
    "https://generativelanguage.googleapis.com/v1/models/gemini-2.5-pro-preview-tts:generateContent",
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro-preview-tts:generateContent",
    "https://generativelanguage.googleapis.com/v1/models/gemma-4-26b-a4b-it:generateContent",
    "https://generativelanguage.googleapis.com/v1beta/models/gemma-4-26b-a4b-it:generateContent",
]


def _call_gemini(key: str, contents: list) -> str:
    payload = _json.dumps({
        "contents": contents,
        "generationConfig": {"temperature": 1, "maxOutputTokens": 16300}
    }).encode()
    headers = {"Content-Type": "application/json", "x-goog-api-key": key}
    last_err = "Ulanmadi"

    for url_base in ENDPOINTS:
        url = f"{url_base}?key={key}"
        for attempt in range(1, 3):
            try:
                req = _ur.Request(url, data=payload, headers=headers, method="POST")
                with _ur.urlopen(req, timeout=6000) as resp:
                    result = _json.loads(resp.read().decode())
                    text = result["candidates"][0]["content"]["parts"][0]["text"]
                    logging.info(f"✅ Gemini: {url_base.split('models/')[1].split(':')[0]}")
                    return text
            except _ue.HTTPError as e:
                e.read()
                if e.code == 404:
                    last_err = "404"; break
                elif e.code == 429:
                    if attempt < 2:
                        time.sleep(15); continue
                    # 429 bo'lsa keyingi modeldma sinash
                    last_err = "429"; break
                elif e.code in (401, 403):
                    return "❌ API kalit noto'g'ri. GEMINI_API_KEY ni tekshiring."
                else:
                    last_err = str(e.code); break
            except Exception as e:
                last_err = str(e)[:50]; break

    if "429" in last_err:
        return "⏳ Gemini limiti tugdi. Biroz kuting va qayta yozing."
    return f"❌ Xato: {last_err}. Qayta urinib ko'ring."


async def handle_ai_chat(request):
    cors = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, x-goog-api-key",
    }
    try:
        data    = await request.json()
        message = data.get("message", "").strip()
        hist    = data.get("history", [])
        images  = data.get("images", [])

        key = (os.environ.get("GEMINI_API_KEY") or
               os.environ.get("GOOGLE_API_KEY", "")).strip()
        if not key:
            return web.json_response(
                {"error": "GEMINI_API_KEY sozlanmagan!"}, headers=cors)

        contents = [
            {"role": "user",  "parts": [{"text": AI_SYSTEM}]},
            {"role": "model", "parts": [{"text": "Tushunarli! Yordam beraman."}]},
        ]
        for h in hist[-10:]:
            role = "model" if h.get("role") == "model" else "user"
            contents.append({"role": role, "parts": [{"text": h.get("content", "")}]})

        parts = []
        if message: parts.append({"text": message})
        for img in images[:2]:
            parts.append({"inline_data": {
                "mime_type": img.get("type", "image/jpeg"),
                "data": img.get("data", "")
            }})
        if not parts: parts.append({"text": "Salom"})
        contents.append({"role": "user", "parts": parts})

        text = _call_gemini(key, contents)
        return web.json_response({"response": text}, headers=cors)

    except Exception as e:
        return web.json_response(
            {"error": f"Server xato: {str(e)[:80]}"}, headers=cors)


async def handle_cors(request):
    return web.Response(headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, x-goog-api-key",
    })


async def start_web_server():
    app = web.Application()
    app.add_routes([
        web.get("/",            lambda r: web.Response(text="MackoMebelBot OK!")),
        web.post("/ai/chat",    handle_ai_chat),
        web.options("/ai/chat", handle_cors),
    ])
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"✅ Web server: port {port}")


async def set_commands(bot: Bot):
    await bot.set_my_commands([
        BotCommand(command="start", description="▶️ Botni ishga tushirish"),
        BotCommand(command="myid",  description="🔢 Mening Telegram ID im"),
    ])


async def main():
    await start_web_server()
    init_db()
    ensure_no_image_placeholder()
    init_qr_dir(DATA_DIR)

    bot = Bot(token=BOT_TOKEN,
              default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp  = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(AutoInitMiddleware())
    dp.callback_query.middleware(AutoInitMiddleware())

    dp.include_router(start.router)
    dp.include_router(language.router)
    dp.include_router(menu.router)
    dp.include_router(categories.router)
    dp.include_router(admin_mgr.router)
    dp.include_router(stats.router)
    dp.include_router(movement.router)
    dp.include_router(manual_add.router)
    dp.include_router(manual_delete.router)
    dp.include_router(add_products.router)
    dp.include_router(delete_products.router)
    dp.include_router(warehouse.router)
    dp.include_router(qr_handler.router)
    dp.include_router(scanner.router)
    dp.include_router(lists.router)
    dp.include_router(photo_upload.router)
    dp.include_router(excel_export.router)
    dp.include_router(history.router)
    dp.include_router(macko_ai_handler.router)
    dp.include_router(search.router)   # ← eng oxirda

    await bot.delete_webhook(drop_pending_updates=True)
    await set_commands(bot)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
