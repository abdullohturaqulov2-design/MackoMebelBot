# -*- coding: utf-8 -*-
import os
import uuid
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import db
from config import IMAGES_DIR
from locales.texts import t
from keyboards.reply import get_main_keyboard
from states.states import AdminStates, PhotoStates
from utils.access import is_admin, get_role_level
from utils.render import send_product_detail

router = Router()



# ── "📷 Rasm yuklash" inline tugmasi bosilganda ─────────────────────────────
@router.callback_query(F.data.startswith("photo:up:"))
async def cb_photo_upload(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer(); return

    lang   = db.get_user_lang(callback.from_user.id)
    prod_id = int(callback.data.split(":")[2])

    await state.update_data(photo_prod_id=prod_id)
    await state.set_state(PhotoStates.waiting_photo)

    from keyboards.reply import cancel_only_keyboard
    await callback.message.answer(
        t(lang, "photo_upload_prompt"),
        reply_markup=cancel_only_keyboard(lang)
    )
    await callback.answer()


# ── Admin rasm yuborganda ────────────────────────────────────────────────────
@router.message(PhotoStates.waiting_photo, F.photo)
async def got_photo(message: Message, state: FSMContext, bot: Bot):
    lang   = db.get_user_lang(message.from_user.id)
    data   = await state.get_data()
    prod_id = data.get("photo_prod_id")

    if not prod_id:
        await state.set_state(AdminStates.main_menu); return

    # Eng katta o'lchamdagi rasmni yuklab olish
    photo      = message.photo[-1]
    file_info  = await bot.get_file(photo.file_id)
    ext        = ".jpg"
    filename   = f"prod_{prod_id}_{uuid.uuid4().hex[:8]}{ext}"
    save_path  = os.path.join(IMAGES_DIR, filename)

    await bot.download_file(file_info.file_path, destination=save_path)

    # Eski rasmni o'chirish (agar bor bo'lsa)
    prod = db.get_product(prod_id)
    if prod and prod["image_path"] and os.path.exists(prod["image_path"]):
        try:
            os.remove(prod["image_path"])
        except OSError:
            pass

    # DBga yangi rasm yo'lini saqlash
    conn = db.get_conn(); c = conn.cursor()
    c.execute("UPDATE products SET image_path=? WHERE id=?", (save_path, prod_id))
    conn.commit(); conn.close()

    await message.answer(t(lang, "photo_saved"))

    # Mahsulot detailini yangilab ko'rsatish
    prod = db.get_product(prod_id)
    role = get_role_level(message.from_user.id)
    await state.set_state(AdminStates.main_menu)
    await message.answer(t(lang, "main_menu"), reply_markup=get_main_keyboard(lang, role))
    if prod:
        await send_product_detail(message, lang, prod, "catshow", admin=True)


# ── Rasm o'rniga boshqa narsa yuborilsa ─────────────────────────────────────
@router.message(PhotoStates.waiting_photo)
async def wrong_photo(message: Message):
    lang = db.get_user_lang(message.from_user.id)
    # /cancel buyrug'i
    if message.text and message.text.strip().lower() in ("/cancel", "bekor", "отмена"):
        from keyboards.reply import get_main_keyboard
        role = get_role_level(message.from_user.id)
        from aiogram.fsm.context import FSMContext
        await message.answer(t(lang, "photo_cancel"),
                             reply_markup=get_main_keyboard(lang, role))
        return
    await message.answer(t(lang, "photo_invalid"))


# ── "🗑 Rasmni o'chirish" inline tugmasi ────────────────────────────────────
@router.callback_query(F.data.startswith("photo:del:"))
async def cb_photo_delete(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer(); return

    lang    = db.get_user_lang(callback.from_user.id)
    prod_id = int(callback.data.split(":")[2])
    prod    = db.get_product(prod_id)

    if prod and prod["image_path"] and os.path.exists(prod["image_path"]):
        try:
            os.remove(prod["image_path"])
        except OSError:
            pass

    conn = db.get_conn(); c = conn.cursor()
    c.execute("UPDATE products SET image_path=NULL WHERE id=?", (prod_id,))
    conn.commit(); conn.close()

    await callback.answer(t(lang, "photo_removed"), show_alert=True)

    # Yangilangan detailni ko'rsat
    prod = db.get_product(prod_id)
    if prod:
        await send_product_detail(callback, lang, prod, "catshow", admin=True)
