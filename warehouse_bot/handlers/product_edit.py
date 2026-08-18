# -*- coding: utf-8 -*-
"""
Mahsulotni tahrirlash va skidka berish.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import db
from locales.texts import t
from states.states import AdminStates
from utils.access import is_admin
from utils.render import send_product_detail, safe_edit_or_send, delete_msg

router = Router()


def _edit_menu_kb(lang, prod_id, back_cb):
    b = InlineKeyboardBuilder()
    fields = [
        ("📦 Nomi",         f"pedit:{prod_id}:name"),
        ("🔢 Kodi",         f"pedit:{prod_id}:code"),
        ("📐 Format",        f"pedit:{prod_id}:format_size"),
        ("📏 Qalinlik",      f"pedit:{prod_id}:thickness"),
        ("💰 Narx",         f"pedit:{prod_id}:price"),
        ("📊 Miqdor",       f"pedit:{prod_id}:quantity"),
        ("📍 Joylashuv",    f"pedit:{prod_id}:location"),
        ("🏷 Skidka",       f"pedit:{prod_id}:discount"),
        ("❌ Skidkani bekor", f"pedit:{prod_id}:nodiscount"),
    ]
    for label, cb in fields:
        b.button(text=label, callback_data=cb)
    b.adjust(2)
    b.row(InlineKeyboardButton(text="🔙 Ortga", callback_data=back_cb))
    return b.as_markup()


@router.callback_query(F.data.startswith("prod_edit:"))
async def cb_prod_edit_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): await callback.answer(); return
    lang    = db.get_user_lang(callback.from_user.id)
    pid     = int(callback.data.split(":")[1])
    back_cb = callback.data.split(":")[2] if len(callback.data.split(":")) > 2 else "catshow"
    prod    = db.get_product(pid)
    if not prod: await callback.answer("Topilmadi", show_alert=True); return
    await state.update_data(editing_prod_id=pid, editing_back_cb=back_cb)
    await safe_edit_or_send(
        callback,
        f"✏️ <b>Tahrirlash:</b> {prod['name']}\n\nQaysi maydonni o'zgartirasiz?",
        _edit_menu_kb(lang, pid, back_cb)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pedit:"))
async def cb_pedit_field(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): await callback.answer(); return
    lang  = db.get_user_lang(callback.from_user.id)
    parts = callback.data.split(":")
    pid   = int(parts[1])
    field = parts[2]

    if field == "nodiscount":
        db.remove_discount(pid)
        prod = db.get_product(pid)
        data = await state.get_data()
        back = data.get("editing_back_cb","catshow")
        await delete_msg(callback.message)
        await send_product_detail(callback, lang, prod, back, admin=True)
        await callback.answer("✅ Skidka bekor qilindi", show_alert=True)
        return

    labels = {
        "name": "📦 Yangi nomini yozing:",
        "code": "🔢 Yangi kodini yozing:",
        "format_size": "📐 Yangi formatni yozing (masalan 2800*2070):",
        "thickness": "📏 Yangi qalinlikni yozing (masalan 18mm):",
        "price": "💰 Yangi narxni yozing (so'm):",
        "quantity": "📊 Yangi miqdorni yozing:",
        "location": "📍 Yangi joylashuvni yozing:",
        "discount": "🏷 Skidka narxini yozing (so'm):\n\nMisol: 450000 → 375000",
    }

    prod = db.get_product(pid)
    if not prod: await callback.answer(); return

    current_vals = {
        "name": prod["name"], "code": prod["code"] or "-",
        "format_size": prod["format_size"] or "-", "thickness": prod["thickness"] or "-",
        "price": str(int(prod["price"] or 0)), "quantity": str(int(prod["quantity"] or 0)),
        "location": prod["location"] or "-",
        "discount": str(int(prod.get("discount_price") or 0)),
    }

    await state.update_data(editing_field=field, editing_prod_id=pid)
    await state.set_state(AdminStates.editing_product)
    await callback.message.answer(
        f"<b>Hozirgi qiymat:</b> <code>{current_vals.get(field,'-')}</code>\n\n"
        f"{labels.get(field,'Yangi qiymat:')}",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.editing_product, F.text)
async def got_edit_value(message: Message, state: FSMContext):
    lang = db.get_user_lang(message.from_user.id)
    data = await state.get_data()
    pid  = data.get("editing_prod_id")
    field= data.get("editing_field")
    back = data.get("editing_back_cb","catshow")
    val  = message.text.strip()

    if field == "discount":
        try:
            discount = float(val.replace(" ","").replace(",","."))
            db.set_discount(pid, discount)
            await message.answer(
                f"✅ Skidka belgilandi!\n"
                f"💰 Narx: <s>{int(db.get_product(pid)['price'] or 0):,}</s> → "
                f"<b>{int(discount):,} so'm</b> 🏷",
                parse_mode="HTML"
            )
        except ValueError:
            await message.answer("⚠️ Noto'g'ri narx. Son kiriting:"); return
    elif field in ("price","quantity","min_quantity"):
        try:
            num = float(val.replace(" ","").replace(",","."))
            db.update_product_field(pid, field, num)
            await message.answer(f"✅ {field} yangilandi: <b>{num}</b>", parse_mode="HTML")
        except ValueError:
            await message.answer("⚠️ Son kiriting:"); return
    else:
        db.update_product_field(pid, field, val)
        await message.answer(f"✅ Yangilandi: <b>{val}</b>", parse_mode="HTML")

    prod = db.get_product(pid)
    await state.set_state(AdminStates.main_menu)
    await send_product_detail(message, lang, prod, back, admin=True)
