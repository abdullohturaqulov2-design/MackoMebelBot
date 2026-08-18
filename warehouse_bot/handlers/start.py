# -*- coding: utf-8 -*-
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from database import db
from keyboards.reply import get_main_keyboard, language_keyboard
from locales.texts import t
from states.states import AdminStates
from utils.access import get_role_level

router = Router()

WELCOME_BANNER = """
╔══════════════════════════╗
║   🏭 MACKO MEBEL BOT    ║
╚══════════════════════════╝"""

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    uid  = message.from_user.id
    name = message.from_user.first_name or message.from_user.username or "Foydalanuvchi"

    if not db.user_has_language(uid):
        db.upsert_user(uid, message.from_user.username, message.from_user.full_name)
        await state.set_state(AdminStates.choosing_language)
        await message.answer(
            f"👋 <b>Assalomu alaykum, {name}!</b>\n\n"
            "🌐 Iltimos, tilni tanlang:",
            parse_mode="HTML",
            reply_markup=language_keyboard()
        )
        return

    lang = db.get_user_lang(uid)
    role = get_role_level(uid)
    await state.set_state(AdminStates.main_menu)

    # Chiroyli xush kelibsiz
    welcome = (
        f"<pre>{WELCOME_BANNER}</pre>\n\n"
        f"👋 <b>Xush kelibsiz, {name}!</b>\n\n"
        f"📦 <b>Macko Mebel</b> ombori boshqaruv tizimi\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ Mahsulotlarni qidirish va ko'rish\n"
        f"✅ Kirim / Chiqim boshqaruvi\n"
        f"✅ Excel orqali yuklash\n"
        f"✅ QR kod va rasm qidirish\n"
        f"✅ 🤖 Macko AI yordamchisi\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👇 <b>Quyidagi menyudan boshlang:</b>"
    )
    await message.answer(
        welcome,
        parse_mode="HTML",
        reply_markup=get_main_keyboard(lang, role)
    )


@router.message(Command("myid"))
async def cmd_myid(message: Message):
    uid  = message.from_user.id
    lang = db.get_user_lang(uid)
    await message.answer(
        t(lang, "myid_response", uid=uid),
        parse_mode="HTML"
    )
