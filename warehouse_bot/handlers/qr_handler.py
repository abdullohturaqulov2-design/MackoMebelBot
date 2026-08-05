# -*- coding: utf-8 -*-
"""
1. "QR code berish" tugmasi bosilganda QR yaratadi
2. /start qr_KOD deep link ni qayta ishlaydi
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext

from database import db
from locales.texts import t
from utils.access import is_admin, get_role_level
from utils.render import send_product_detail

router = Router()


# ── "QR code berish" tugmasi ─────────────────────────────────────────────────
@router.callback_query(F.data.startswith("qr:gen:"))
async def cb_qr_generate(callback: CallbackQuery):
    uid  = callback.from_user.id
    if not is_admin(uid): await callback.answer(); return
    lang = db.get_user_lang(uid)
    pid  = int(callback.data.split(":")[2])
    prod = db.get_product(pid)
    if not prod: await callback.answer("Topilmadi", show_alert=True); return

    try:
        from utils.qr_utils import generate_qr
        qr_path = generate_qr(prod["code"] or "", pid, prod.get("name",""))
        if qr_path:
            code_text = prod["code"] or f"#{pid}"
            await callback.message.answer_photo(
                photo=FSInputFile(qr_path),
                caption=(
                    f"✅ QR Code yaratildi!\n\n"
                    f"📦 <b>{prod['name']}</b>\n"
                    f"📦 QR Code: <code>{code_text}</code>\n\n"
                    f"💡 Tashqi skaner bilan skanerlaganda Telegram ochiladi."
                ),
                parse_mode="HTML"
            )
            # Klaviaturani yangilash (QR tugmasini yashirish)
            await send_product_detail(callback, lang, prod, "catshow", admin=True)
        else:
            await callback.answer("❌ QR yaratib bo'lmadi", show_alert=True)
    except Exception as e:
        await callback.answer(f"Xato: {e}", show_alert=True)
    await callback.answer()


# ── /start qr_KOD deep link ──────────────────────────────────────────────────
@router.message(CommandStart(deep_link=True))
async def cmd_start_deeplink(message: Message, command: CommandObject, state: FSMContext):
    args = command.args or ""

    # qr_ prefiksi bilan kelsa — mahsulot qidirish
    if args.startswith("qr_"):
        code = args[3:]  # "qr_AKR001" → "AKR001"
        uid  = message.from_user.id
        lang = db.get_user_lang(uid)

        products = db.search_by_code(code)
        if not products:
            # ID bo'yicha qidirish
            try:
                prod = db.get_product(int(code))
                if prod: products = [prod]
            except (ValueError, TypeError):
                pass

        if products:
            await message.answer(f"✅ QR skanerlandi: <code>{code}</code>", parse_mode="HTML")
            await send_product_detail(message, lang, products[0], "catshow",
                                      admin=is_admin(uid))
        else:
            await message.answer(
                f"❌ <code>{code}</code> kodi bo'yicha mahsulot topilmadi.",
                parse_mode="HTML")
        return

    # Oddiy /start — asosiy handler ga o'tkazish
    from handlers.start import cmd_start as _start
    await _start(message, state)
