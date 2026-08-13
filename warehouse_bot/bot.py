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

import os, json as _json, time, logging
import urllib.request as _ur
import urllib.error as _ue

AI_SYSTEM = """Siz MackoMebelBot uchun Macko AI yordamchisisiz.
Mebel, plita, akril, MDF, XDF, laminat, kromka haqida maslahat beradi.
O'zbek, rus va ingliz tillarida gaplashadi. Qisqa va aniq javoblar beradi.
Iltimos hech qanday chuqur uylamangda max 250 ta so'z va chiroyli stikerlar bilan foydalanuvchiga tushunarli javob bering
Yana iltimos bitta javobni qayta qayta takrorlaab yubormang yana bir narsa ko'p uylamangda tez-tez va anniq javoblarni bering. 
Agarda foydalanuvchi rasm tashlasa va tahlil qilishni surasa rasm tashlash hajmini tushuntiring va qaytadan rasm tashlashini ayting hamda ko'p 
uylab utirmasdan srzu tahlil qilib javob bering yana sizga max rasm tahlil qilib javob berishingiz uchun 2 minutda tahlil qilib bulib javob 
berishiningiz kerak hamda foydalanuvchi boshqa narsa haqida malumot surasa siz ayting biz faqat mebellr haqida malumot bera olamiz deb keyin 
ayting mebellar haqida yoki shu yuzasidan savollar bulsa bering deb"""

# gemini-2.0-flash BIRINCHI — tez va o'ylamaydi!
MODELS = [
    {"url": "https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent",
     "cfg": {"temperature": 1, "maxOutputTokens": 16300}},
    {"url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
     "cfg": {"temperature": 1, "maxOutputTokens": 16300}},
    # 2.5-flash — thinkingBudget:0 bilan (thinking o'chirilgan)
    {"url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
     "cfg": {"temperature": 1, "maxOutputTokens": 16300,
             "thinkingConfig": {"thinkingBudget": 0}}},
    {"url": "https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent",
     "cfg": {"temperature": 1, "maxOutputTokens": 16300,
             "thinkingConfig": {"thinkingBudget": 0}}},
    {"url": "https://generativelanguage.googleapis.com/v1/models/gemini-2.5-pro:generateContent",
     "cfg": {"temperature": 1, "maxOutputTokens": 16300,
             "thinkingConfig": {"thinkingBudget": 0}}},
    {"url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent",
     "cfg": {"temperature": 1, "maxOutputTokens": 16300,
             "thinkingConfig": {"thinkingBudget": 0}}},
    {"url": "https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash-preview-tts:generateContent",
     "cfg": {"temperature": 1, "maxOutputTokens": 16300,
             "thinkingConfig": {"thinkingBudget": 0}}},
    {"url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent",
     "cfg": {"temperature": 1, "maxOutputTokens": 16300,
             "thinkingConfig": {"thinkingBudget": 0}}},
    {"url": "https://generativelanguage.googleapis.com/v1/models/gemini-2.5-pro-preview-tts:generateContent",
     "cfg": {"temperature": 1, "maxOutputTokens": 16300,
             "thinkingConfig": {"thinkingBudget": 0}}},
    {"url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro-preview-tts:generateContent",
     "cfg": {"temperature": 1, "maxOutputTokens": 16300,
             "thinkingConfig": {"thinkingBudget": 0}}},
    {"url": "https://generativelanguage.googleapis.com/v1/models/gemma-4-26b-a4b-it:generateContent",
     "cfg": {"temperature": 1, "maxOutputTokens": 16300,
             "thinkingConfig": {"thinkingBudget": 0}}},
    {"url": "https://generativelanguage.googleapis.com/v1beta/models/gemma-4-26b-a4b-it:generateContent",
     "cfg": {"temperature": 1, "maxOutputTokens": 16300,
             "thinkingConfig": {"thinkingBudget": 0}}},
]


def _clean(text: str) -> str:
    """AI fikrlash artifaktlarini olib tashlaydi (--- va ichki monolog)."""
    lines = text.split('\n')
    result, skip = [], False
    for line in lines:
        s = line.strip()
        if s == '---':
            skip = True; continue
        if skip:
            # Italik yoki "Wait," bilan boshlanadigan satrlar = ichki fikr
            if s.startswith('*') or s.startswith('Wait') or s.startswith('Plan') \
               or s.startswith('Response content') or s.startswith('Let\'s') \
               or s.startswith('Drafting') or s.startswith('Resulting'):
                continue
            if s == '':
                continue
            skip = False
        result.append(line)
    return '\n'.join(result).strip() or text


def _call_gemini(key: str, contents: list) -> str:
    headers = {"Content-Type": "application/json", "x-goog-api-key": key}
    last_err = "Ulanmadi"

    for model in MODELS:
        payload = _json.dumps({
            "contents": contents,
            "generationConfig": model["cfg"]
        }).encode()
        url = f"{model['url']}?key={key}"

        for attempt in range(1, 3):
            try:
                req = _ur.Request(url, data=payload, headers=headers, method="POST")
                with _ur.urlopen(req, timeout=6000) as resp:
                    result = _json.loads(resp.read().decode())
                    raw  = result["candidates"][0]["content"]["parts"][0]["text"]
                    text = _clean(raw)
                    name = model['url'].split('models/')[1].split(':')[0]
                    logging.info(f"✅ {name}")
                    return text
            except _ue.HTTPError as e:
                body = e.read().decode("utf-8", errors="ignore")
                if e.code == 404:
                    last_err = "404"; break
                elif e.code == 429:
                    if attempt < 2: time.sleep(10); continue
                    last_err = "429"; break
                elif e.code == 413:
                    return "❌ Rasm juda katta. Kichikroq rasm yuboring (skrinshot)."
                elif e.code in (401, 403):
                    return "❌ API kalit noto'g'ri."
                else:
                    last_err = f"{e.code}"; break
            except Exception as e:
                last_err = str(e)[:50]; break

    if "429" in str(last_err):
        return "⏳ Limit tugdi. 1 daqiqadan so'ng qayta yozing."
    return f"❌ Xato: {last_err}"


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
            return web.json_response({"error": "GEMINI_API_KEY sozlanmagan!"}, headers=cors)

        contents = [
            {"role": "user",  "parts": [{"text": AI_SYSTEM}]},
            {"role": "model", "parts": [{"text": "Tushunarli! Yordam beraman."}]},
        ]
        for h in hist[-6:]:  # Kam tarix — tezroq
            role = "model" if h.get("role") == "model" else "user"
            contents.append({"role": role, "parts": [{"text": h.get("content", "")[:500]}]})

        parts = []
        if message: parts.append({"text": message})
        for img in images[:1]:  # Max 1 ta rasm
            parts.append({"inline_data": {
                "mime_type": img.get("type", "image/jpeg"),
                "data": img.get("data", "")
            }})
        if not parts: parts.append({"text": "Salom"})
        contents.append({"role": "user", "parts": parts})

        text = _call_gemini(key, contents)
        return web.json_response({"response": text}, headers=cors)

    except Exception as e:
        err = str(e)
        if "Too Large" in err or "413" in err:
            return web.json_response(
                {"error": "Rasm juda katta. Kichikroq rasm yuboring."}, headers=cors)
        return web.json_response({"error": f"Xato: {err[:80]}"}, headers=cors)


async def handle_cors(request):
    return web.Response(headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, x-goog-api-key",
    })

async def start_web_server():
    app = web.Application(client_max_size=5*1024*1024)  # 5MB max
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
