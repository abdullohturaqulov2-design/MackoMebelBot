# -*- coding: utf-8 -*-
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from database import db
from locales.texts import t
from states.states import AdminStates
from utils.access import is_admin
from utils.render import send_product_detail, safe_edit_or_send, delete_msg

router = Router()


def _edit_kb(lang, prod_id, back_cb):
    b = InlineKeyboardBuilder()
    fields = [
        ("📦 Nomi",      f"pe:{prod_id}:name:{back_cb}"),
        ("🔢 Kodi",      f"pe:{prod_id}:code:{back_cb}"),
        ("📐 Format",    f"pe:{prod_id}:format_size:{back_cb}"),
        ("📏 Qalinlik",  f"pe:{prod_id}:thickness:{back_cb}"),
        ("💰 Narx",      f"pe:{prod_id}:price:{back_cb}"),
        ("📊 Miqdor",    f"pe:{prod_id}:quantity:{back_cb}"),
        ("📍 Joylashuv", f"pe:{prod_id}:location:{back_cb}"),
        ("🏷 Skidka",    f"pe:{prod_id}:discount:{back_cb}"),
        ("❌ Skidka bekor", f"pe:{prod_id}:nodiscount:{back_cb}"),
    ]
    for label, cb in fields:
        b.button(text=label, callback_data=cb)
    b.adjust(2)
    b.row(InlineKeyboardButton(text="🔙 Ortga", callback_data=back_cb))
    return b.as_markup()


@router.callback_query(F.data.startswith("prod_edit:"))
async def cb_edit_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer(); return
    lang  = db.get_user_lang(callback.from_user.id)
    parts = callback.data.split(":", 2)
    pid   = int(parts[1])
    back  = parts[2] if len(parts) > 2 else "catshow"
    prod  = db.get_product(pid)
    if not prod:
        await callback.answer("Topilmadi", show_alert=True); return
    await state.update_data(ep_id=pid, ep_back=back)
    await safe_edit_or_send(
        callback,
        f"✏️ <b>Tahrirlash:</b> {prod['name']}\n\nQaysi maydonni o'zgartirmoqchisiz?",
        _edit_kb(lang, pid, back))
    await callback.answer()


@router.callback_query(F.data.startswith("pe:"))
async def cb_edit_field(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer(); return
    lang  = db.get_user_lang(callback.from_user.id)
    parts = callback.data.split(":", 3)
    pid   = int(parts[1])
    field = parts[2]
    back  = parts[3] if len(parts) > 3 else "catshow"
    prod  = db.get_product(pid)
    if not prod:
        await callback.answer(); return

    if field == "nodiscount":
        db.set_discount(pid, 0)
        await delete_msg(callback.message)
        await send_product_detail(callback, lang, prod, back, admin=True)
        await callback.answer("✅ Skidka bekor qilindi", show_alert=True)
        return

    labels = {
        "name":        f"📦 Nomi (hozir: <code>{prod['name']}</code>)",
        "code":        f"🔢 Kodi (hozir: <code>{prod['code'] or '-'}</code>)",
        "format_size": f"📐 Format (hozir: <code>{prod['format_size'] or '-'}</code>)",
        "thickness":   f"📏 Qalinlik (hozir: <code>{prod['thickness'] or '-'}</code>)",
        "price":       f"💰 Narx (hozir: <code>{int(prod['price'] or 0):,}</code> so'm)",
        "quantity":    f"📊 Miqdor (hozir: <code>{int(prod['quantity'] or 0)}</code>)",
        "location":    f"📍 Joylashuv (hozir: <code>{prod['location'] or '-'}</code>)",
        "discount":    f"🏷 Skidka narxi (hozir: <code>{int(prod.get('discount_price') or 0):,}</code> so'm)\n\n"
                       f"Misol: asosiy narx 450000 bo'lsa, skidka narxi 375000 kiriting",
    }

    await state.update_data(ep_id=pid, ep_field=field, ep_back=back)
    await state.set_state(AdminStates.editing_product)
    await callback.message.answer(
        f"✏️ <b>Yangi qiymat kiriting:</b>\n\n{labels.get(field,'Yangi qiymat:')}",
        parse_mode="HTML")
    await callback.answer()


@router.message(AdminStates.editing_product, F.text)
async def got_edit_value(message: Message, state: FSMContext):
    lang = db.get_user_lang(message.from_user.id)
    data = await state.get_data()
    pid   = data.get("ep_id")
    field = data.get("ep_field")
    back  = data.get("ep_back", "catshow")
    val   = message.text.strip()

    if not pid or not field:
        await state.set_state(AdminStates.main_menu)
        return

    # Validatsiya
    if field in ("price", "quantity", "min_quantity", "discount"):
        try:
            val = float(val.replace(" ", "").replace(",", "."))
            if val < 0: raise ValueError
        except ValueError:
            await message.answer("⚠️ Son kiriting (musbat):"); return

    # Saqlash
    if field == "discount":
        db.set_discount(pid, val)
        prod = db.get_product(pid)
        p_str = f"{int(prod['price'] or 0):,}".replace(",", " ")
        d_str = f"{int(val):,}".replace(",", " ")
        await message.answer(
            f"✅ Skidka belgilandi!\n"
            f"💰 <s>{p_str}</s> → <b>{d_str} so'm</b> 🏷",
            parse_mode="HTML")
    else:
        db.update_product_field(pid, field, val)
        await message.answer(f"✅ Yangilandi!", parse_mode="HTML")

    await state.set_state(AdminStates.main_menu)
    prod = db.get_product(pid)
    await send_product_detail(message, lang, prod, back, admin=True)
