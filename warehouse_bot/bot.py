# -*- coding: utf-8 -*-
import asyncio
import logging
import os
from aiohttp import web

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from handlers import scanner
from utils.qr_utils import init_qr_dir

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

async def start_web_server():
    app = web.Application()
    app.add_routes([web.get("/", handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()


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
    dp.include_router(history.router)
    dp.include_router(search.router)       # ← eng oxirda

    await bot.delete_webhook(drop_pending_updates=True)
    await set_commands(bot)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())