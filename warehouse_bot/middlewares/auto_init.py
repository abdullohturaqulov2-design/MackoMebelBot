# -*- coding: utf-8 -*-
"""
/start bosilmasa ham bot ishlaydi:
- Foydalanuvchi avtomatik ro'yxatdan o'tkaziladi
- State main_menu ga o'rnatiladi
- Birinchi marta klaviatura avtomatik ko'rsatiladi
"""
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from database import db
from states.states import AdminStates


class AutoInitMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user
        else:
            return await handler(event, data)

        if not user or user.is_bot:
            return await handler(event, data)

        # DB ga yozish
        db.upsert_user(user.id, user.username, user.full_name)

        # FSM holatini tekshirish
        fsm      = data.get("state")
        was_none = False

        if fsm:
            current = await fsm.get_state()
            if current is None:
                was_none = True
                if db.user_has_language(user.id):
                    await fsm.set_state(AdminStates.main_menu)
                else:
                    await fsm.set_state(AdminStates.choosing_language)

        # Handlerni ishlatish
        result = await handler(event, data)

        # Birinchi marta: klaviatura ko'rsat
        if was_none and isinstance(event, Message) and db.user_has_language(user.id):
            try:
                from utils.access import get_role_level
                from keyboards.reply import get_main_keyboard
                from locales.texts import t
                lang = db.get_user_lang(user.id)
                role = get_role_level(user.id)
                await event.answer(
                    t(lang, "main_menu"),
                    reply_markup=get_main_keyboard(lang, role)
                )
            except Exception:
                pass

        return result
