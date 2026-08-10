# -*- coding: utf-8 -*-
import asyncio
import logging
import os
from aiohttp import web
import json as _json

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from handlers import scanner
from utils.qr_utils import init_qr_dir
from handlers import macko_ai_handler
from handlers import excel_export
from handlers import qr_handler
from config import BOT_TOKEN
from database.db import init_db
from utils.image_utils import ensure_no_image_placeholder
from middlewares.auto_init import AutoInitMiddleware

from handlers import (start, language, menu, categories, admin_mgr,
                      add_products, delete_products, stats, movement,
                      warehouse, lists, search, photo_upload, history,
                      manual_add, manual_delete)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

# Render "Live" holatiga o'tkazishi uchun kichik veb-server
async def handle(request):
    return web.Response(text="Bot is running and alive!")

AI_SYSTEM = """Siz MackoMebelBot uchun Macko AI yordamchisisiz.
Mebel, plita, akril, MDF, XDF, laminat, kromka haqida maslahat beradi.
O'zbek, rus va ingliz tillarida gaplashadi. Qisqa va aniq javoblar beradi."""

async def handle_ai_chat(request):
    """Macko AI mini app uchun Gemini proxy."""
    import urllib.request as _ur
    try:
        data = await request.json()
        message  = data.get('message','')
        history  = data.get('history',[])
        images   = data.get('images',[])

        key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY','')
        if not key:
            return web.json_response({'error':'GEMINI_API_KEY sozlanmagan'})

        # Suhbat tarixi
        contents = [{'role':'user','parts':[{'text':AI_SYSTEM}]},
                    {'role':'model','parts':[{'text':'Tushunarli! Macko AI sifatida yordam beraman.'}]}]

        for h in history[-10:]:
            role = 'model' if h['role']=='model' else 'user'
            contents.append({'role':role,'parts':[{'text':h['content']}]})

        # Joriy xabar (rasm bilan)
        parts = []
        if message: parts.append({'text':message})
        for img in images[:3]:
            parts.append({'inline_data':{'mime_type':img.get('type','image/jpeg'),'data':img['data']}})
        if not parts: parts.append({'text':'Salom'})
        contents.append({'role':'user','parts':parts})

        payload = _json.dumps({
            'contents':contents,
            'generationConfig':{'maxOutputTokens':2048,'temperature':0.7}
        }).encode()

        req = _ur.Request(
            f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}',
            data=payload, headers={'Content-Type':'application/json'}, method='POST')
        with _ur.urlopen(req, timeout=30) as resp:
            result = _json.loads(resp.read())

        text = result['candidates'][0]['content']['parts'][0]['text']
        return web.json_response({'response':text},
            headers={'Access-Control-Allow-Origin':'*'})

    except Exception as e:
        return web.json_response({'error':str(e)},
            headers={'Access-Control-Allow-Origin':'*'})

async def handle_cors(request):
    return web.Response(headers={
        'Access-Control-Allow-Origin':'*',
        'Access-Control-Allow-Methods':'POST,GET,OPTIONS',
        'Access-Control-Allow-Headers':'Content-Type'
    })

async def handle_ping(request):
    return web.Response(text="MackoMebelBot ishlayapti OK!")

async def start_web_server():
    app = web.Application()
    app.add_routes([
        web.get("/",   handle_ping),
        web.post("/ai/chat", handle_ai_chat),
        web.options("/ai/chat", handle_cors),  # CORS
    ])
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Web server: http://0.0.0.0:{port}")


async def set_commands(bot: Bot):
    """Faqat /start command tugmasi."""
    await bot.set_my_commands([
        BotCommand(command="start",  description="▶️ Botni ishga tushirish"),
        BotCommand(command="myid",   description="🔢 Mening Telegram ID im"),
    ])


async def main():
    await start_web_server()

    init_db()
    ensure_no_image_placeholder()

    # ← BU QATORNI QO'SHING:
    from config import DATA_DIR
    init_qr_dir(DATA_DIR)


    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # ── Middleware (auto-init — /start bosilmasa ham ishlaydi) ───────────────
    dp.message.middleware(AutoInitMiddleware())
    dp.callback_query.middleware(AutoInitMiddleware())

    # ── Routerlar (tartib muhim — search eng oxirda) ─────────────────────────
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
    dp.include_router(search.router)       # ← eng oxirda

    await bot.delete_webhook(drop_pending_updates=True)
    await set_commands(bot)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())