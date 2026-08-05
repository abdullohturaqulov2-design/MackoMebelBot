# -*- coding: utf-8 -*-
import os
from typing import Optional, Sequence, Union
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.exceptions import TelegramBadRequest

from database import db
from locales.texts import t
from keyboards.inline import (paginate, products_list_keyboard,
                               product_detail_back_keyboard,
                               product_detail_admin_keyboard)
from utils.image_utils import ensure_no_image_placeholder


def _qty_str(qty, min_qty):
    s = str(int(qty) if qty == int(qty) else qty)
    if min_qty and min_qty > 0:
        return f"{s} ⚠️ (min: {int(min_qty)})" if qty < min_qty else f"{s} ✅"
    return s


def format_detail(lang, prod):
    cat    = prod["category"] or ""
    subcat = prod["subcategory"] or ""
    keys   = prod.keys() if hasattr(prod, "keys") else prod.keys()
    min_q  = prod["min_quantity"] if "min_quantity" in keys else 0
    price  = prod["price"] if "price" in keys else 0
    price_str = f"{int(price):,}".replace(",", " ") if price else "-"
    return t(lang, "product_detail",
        name        = prod["name"],
        code        = prod["code"] or "-",
        category    = db.get_category_label(lang, cat),
        subcategory = db.get_subcategory_label(lang, cat, subcat),
        format_size = prod["format_size"] or "-",
        thickness   = prod["thickness"] or "-",
        price       = price_str,
        qty_str     = _qty_str(prod["quantity"], min_q),
        location    = prod["location"] or "-",
        added_at    = prod["added_at"],
    )


async def delete_msg(message):
    """Xabarni o'chirish (xato bo'lsa jim o'tish)."""
    try:
        await message.delete()
    except Exception:
        pass


async def safe_edit_or_send(cb: CallbackQuery, text: str, markup=None):
    """
    Xabarni edit qilishga harakat qiladi.
    Agar edit bo'lmasa (masalan rasm xabari) — eski xabarni o'chirib yangi yuboradi.
    """
    try:
        await cb.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    except TelegramBadRequest:
        # Rasm yoki boshqa media xabari — o'chirib yangisini yuborish
        await delete_msg(cb.message)
        await cb.message.answer(text, reply_markup=markup, parse_mode="HTML")


async def send_products_list(
    target, lang, rows, page,
    item_prefix, nav_prefix, title_key,
    back_cb=None, edit=False,
):
    if not rows:
        text = t(lang, "no_products_here")
        kb   = product_detail_back_keyboard(lang, back_cb) if back_cb else None
        if edit and isinstance(target, CallbackQuery):
            await safe_edit_or_send(target, text, kb)
        else:
            msg = target.message if isinstance(target, CallbackQuery) else target
            await msg.answer(text, reply_markup=kb, parse_mode="HTML")
        return

    items, page, total = paginate(rows, page)
    kb   = products_list_keyboard(lang, items, page, total,
                                   item_prefix, nav_prefix, back_cb)
    text = t(lang, title_key, page=page + 1, total=total)

    if edit and isinstance(target, CallbackQuery):
        await safe_edit_or_send(target, text, kb)
    else:
        msg = target.message if isinstance(target, CallbackQuery) else target
        await msg.answer(text, reply_markup=kb, parse_mode="HTML")


async def send_product_detail(target, lang, prod, back_cb, admin=False):
    from aiogram.types import FSInputFile, InputMediaPhoto, CallbackQuery
    text     = format_detail(lang, prod)
    img      = prod["image_path"] if prod["image_path"] else None
    has_photo= bool(img and os.path.exists(img))

    # QR holati
    has_qr = False
    qr_path = None
    try:
        from utils.qr_utils import get_or_create_qr, has_qr as _hq
        has_qr  = _hq(prod)
        qr_path = get_or_create_qr(prod)
    except Exception:
        pass

    kb  = (product_detail_admin_keyboard(lang, prod["id"], back_cb,
                                         has_photo=has_photo, has_qr=has_qr)
           if admin else product_detail_back_keyboard(lang, back_cb))
    msg = target.message if isinstance(target, CallbackQuery) else target

    if isinstance(target, CallbackQuery):
        await delete_msg(target.message)

    # Rasm + QR birga
    if has_photo and qr_path and os.path.exists(qr_path):
        try:
            code_text = prod["code"] or f"#{prod['id']}"
            await msg.answer_media_group([
                InputMediaPhoto(media=FSInputFile(img), caption=text, parse_mode="HTML"),
                InputMediaPhoto(media=FSInputFile(qr_path),
                                caption=f"📦 QR Code: <code>{code_text}</code>",
                                parse_mode="HTML"),
            ])
            await msg.answer("​", reply_markup=kb)
            return
        except Exception:
            pass

    # Faqat rasm
    photo = FSInputFile(img) if has_photo else FSInputFile(ensure_no_image_placeholder())
    await msg.answer_photo(photo=photo, caption=text, reply_markup=kb, parse_mode="HTML")

    # QR alohida
    if qr_path and os.path.exists(qr_path) and not has_photo:
        code_text = prod["code"] or f"#{prod['id']}"
        await msg.answer_photo(photo=FSInputFile(qr_path),
                               caption=f"📦 QR Code: <code>{code_text}</code>",
                               parse_mode="HTML")