# -*- coding: utf-8 -*-
"""
1. "🤖 Macko AI" tugmasi bosilganda WebApp ochadi
2. Foydalanuvchi rasm yuborganda chiroyli Macko AI ga yo'naltiradi
"""
import os
from aiogram import Router, F
from aiogram.types import (Message, InlineKeyboardMarkup,
                           InlineKeyboardButton, WebAppInfo)
from aiogram.fsm.context import FSMContext

from database import db
from locales.texts import TEXTS
from utils.render import delete_msg

router = Router()

def _all(k): return {TEXTS[l].get(k,"") for l in TEXTS} - {""}

def _get_ai_url() -> str:
    url     = os.environ.get("WEBAPP_AI_URL","").strip()
    bot_url = os.environ.get("BOT_URL","").strip().rstrip("/")
    if not url: return ""
    return f"{url}?bot={bot_url}" if bot_url else url


# ── "🤖 Macko AI" tugmasi ─────────────────────────────────────────────────────
@router.message(F.text.in_(_all("btn_macko_ai")))
async def open_macko_ai(message: Message):
    await delete_msg(message)
    lang = db.get_user_lang(message.from_user.id)
    url  = _get_ai_url()

    if not url:
        await message.answer(
            "⚠️ Macko AI hali sozlanmagan.\n\n"
            "Render → Environment ga qo'shing:\n"
            "<code>WEBAPP_AI_URL=...</code>\n"
            "<code>BOT_URL=https://...</code>",
            parse_mode="HTML"
        )
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🤖 Macko AI ni ochish",
            web_app=WebAppInfo(url=url)
        )
    ]])

    await message.answer(
        "🤖 <b>Macko AI</b>\n\n"
        "Sun'iy intellekt yordamida:\n"
        "• 💬 Mebel haqida savol bering\n"
        "• 🖼 Rasmni yuklang — tahlil qilaman\n"
        "• 📦 Mahsulot maslahat so'rang\n"
        "• 🌐 O'zbek / Rus / Ingliz tilida\n\n"
        "⬇️ Pastdagi tugmani bosing:",
        parse_mode="HTML",
        reply_markup=kb
    )


# ── Rasm kelganda → Macko AI ga chiroyli yo'naltirish ────────────────────────
@router.message(F.photo)
async def photo_to_macko_ai(message: Message, state: FSMContext):
    """
    Foydalanuvchi rasm yuborganda — Macko AI ga yo'naltiradi.
    Bu handler search.router dan OLDIN ro'yxatdan o'tkazilishi kerak.
    """
    from states.states import PhotoStates, ManualAddStates
    current = await state.get_state()

    # Boshqa handlerlar uchun mo'ljallangan holatlar
    if current in {PhotoStates.waiting_photo.state,
                   ManualAddStates.waiting_image.state}:
        return  # tegishli handler ishlaydi

    lang = db.get_user_lang(message.from_user.id)
    url  = _get_ai_url()

    if url:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🤖 Macko AI da ochish",
                web_app=WebAppInfo(url=url)
            )],
        ])
        await message.answer(
            "🖼 <b>Rasm yubordin!</b>\n\n"
            "📦 Mahsulot haqida ma'lumot kerakmi?\n\n"
            "🤖 <b>Macko AI</b> dan foydalaning:\n"
            "• Rasmni yuklang → AI tahlil qiladi\n"
            "• Mahsulot nomi, turi, rangi aniqlanadi\n"
            "• Savol bersangiz javob beradi\n\n"
            "⬇️ Quyidagi tugmani bosing:",
            parse_mode="HTML",
            reply_markup=kb
        )
    else:
        await message.answer(
            "🤖 Rasm tahlili uchun <b>Macko AI</b> bo'limidan foydalaning!\n\n"
            "Menyu tugmalarida <b>🤖 Macko AI</b> ni bosing.",
            parse_mode="HTML"
        )
