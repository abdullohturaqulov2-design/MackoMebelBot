# -*- coding: utf-8 -*-
"""
Har bir update uchun 4.5 soniya limit.
Bot hech qachon qotmaydi.
"""
import asyncio, logging
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

logger = logging.getLogger(__name__)

class TimeoutMiddleware(BaseMiddleware):
    def __init__(self, timeout: float = 120):
        self.timeout = timeout

    async def __call__(self, handler, event, data):
        try:
            return await asyncio.wait_for(
                handler(event, data),
                timeout=self.timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ Timeout: {type(event).__name__}")
            try:
                if isinstance(event, Message):
                    await event.answer("⏳ Server band. Qayta urinib ko'ring.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("⏳ Kuting...", show_alert=False)
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Handler xato: {e}")
