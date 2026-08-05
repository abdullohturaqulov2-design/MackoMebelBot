# -*- coding: utf-8 -*-
import os, uuid, re
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext

from database import db
from config import IMAGES_DIR
from locales.texts import t
from keyboards.reply import get_main_keyboard, cancel_only_keyboard
from keyboards.inline import (
    ma_categories_keyboard, ma_subcategories_keyboard,
    skip_keyboard, skip_photo_keyboard, ma_confirm_keyboard,
    ma_edit_fields_keyboard,
)
from states.states import AdminStates, ManualAddStates, ManualAddEditStates
from utils.access import is_admin, get_role_level
from utils.render import delete_msg

router = Router()
SLUG_RE = re.compile(r'^[a-zA-Z0-9_]{1,32}$')


async def _show_preview(msg_or_cb, state, lang):
    data = await state.get_data()
    cat_label = db.get_category_label(lang, data.get("ma_category",""))
    sub_label = db.get_subcategory_label(lang, data.get("ma_category",""), data.get("ma_subcategory","")) or "-"
    price = data.get("ma_price", 0)
    price_str = f"{int(price):,}".replace(",", " ") if price else "0"
    text = t(lang, "ma_preview",
             name=data.get("ma_name",""),
             code=data.get("ma_code","") or "-",
             category=cat_label, subcategory=sub_label,
             format_size=data.get("ma_format","") or "-",
             thickness=data.get("ma_thickness","") or "-",
             price=price_str,
             quantity=data.get("ma_quantity", 0),
             location=data.get("ma_location","") or "-")
    msg = msg_or_cb.message if isinstance(msg_or_cb, CallbackQuery) else msg_or_cb
    await msg.answer(text, parse_mode="HTML", reply_markup=ma_confirm_keyboard(lang))


async def start_manual_add(message, state, name):
    lang = db.get_user_lang(message.from_user.id)
    await state.update_data(ma_name=name, ma_code="", ma_category="",
                            ma_subcategory="", ma_format="", ma_thickness="",
                            ma_price=0, ma_quantity=0, ma_location="", ma_image=None)
    await state.set_state(ManualAddStates.waiting_code)
    await message.answer(t(lang,"ma_ask_code"), parse_mode="HTML",
                         reply_markup=skip_keyboard(lang))


# ── 1. KOD ──────────────────────────────────────────────────────────────────
@router.message(ManualAddStates.waiting_code, F.text)
async def ma_got_code(message, state):
    lang = db.get_user_lang(message.from_user.id)
    await state.update_data(ma_code=message.text.strip())
    await _ask_category(message, state, lang)

@router.callback_query(F.data=="ma:skip", ManualAddStates.waiting_code)
async def ma_skip_code(callback, state):
    lang = db.get_user_lang(callback.from_user.id)
    await state.update_data(ma_code=""); await callback.answer()
    await _ask_category(callback.message, state, lang)

async def _ask_category(msg, state, lang):
    cats = db.get_all_categories()
    await state.set_state(ManualAddStates.waiting_category)
    await msg.answer(t(lang,"ma_ask_category"), parse_mode="HTML",
                     reply_markup=ma_categories_keyboard(lang, cats))


# ── 2. KATEGORIYA ────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("macat:"), ManualAddStates.waiting_category)
async def ma_got_category(callback, state):
    lang = db.get_user_lang(callback.from_user.id)
    cat_slug = callback.data.split(":",1)[1]
    await state.update_data(ma_category=cat_slug)
    await callback.answer()
    subs = db.get_subcategories(cat_slug)
    # ✅ FIX: subkategoriya har doim ko'rsatiladi
    await state.set_state(ManualAddStates.waiting_subcategory)
    await callback.message.answer(
        t(lang,"ma_ask_subcat"), parse_mode="HTML",
        reply_markup=ma_subcategories_keyboard(lang, cat_slug, subs))

# Inline yangi kategoriya
@router.callback_query(F.data=="ma:newcat", ManualAddStates.waiting_category)
async def ma_newcat_start(callback, state):
    lang = db.get_user_lang(callback.from_user.id)
    await state.set_state(ManualAddEditStates.new_cat_slug)
    await callback.message.answer(t(lang,"cat_add_slug"), parse_mode="HTML",
                                  reply_markup=cancel_only_keyboard(lang))
    await callback.answer()

@router.message(ManualAddEditStates.new_cat_slug, F.text)
async def ma_newcat_slug(message, state):
    lang = db.get_user_lang(message.from_user.id)
    slug = message.text.strip().lower()
    if not SLUG_RE.match(slug): await message.answer(t(lang,"cat_slug_invalid")); return
    if db.category_exists(slug): await message.answer(t(lang,"cat_slug_exists")); return
    await state.update_data(new_cat_slug=slug)
    await state.set_state(ManualAddEditStates.new_cat_uz)
    await message.answer(t(lang,"cat_add_uz"), parse_mode="HTML")

@router.message(ManualAddEditStates.new_cat_uz, F.text)
async def ma_newcat_uz(message, state):
    await state.update_data(new_cat_uz=message.text.strip())
    await state.set_state(ManualAddEditStates.new_cat_ru)
    await message.answer(t(db.get_user_lang(message.from_user.id),"cat_add_ru"), parse_mode="HTML")

@router.message(ManualAddEditStates.new_cat_ru, F.text)
async def ma_newcat_ru(message, state):
    await state.update_data(new_cat_ru=message.text.strip())
    await state.set_state(ManualAddEditStates.new_cat_en)
    await message.answer(t(db.get_user_lang(message.from_user.id),"cat_add_en"), parse_mode="HTML")

@router.message(ManualAddEditStates.new_cat_en, F.text)
async def ma_newcat_en(message, state):
    lang = db.get_user_lang(message.from_user.id)
    data = await state.get_data()
    db.add_category(data["new_cat_slug"],data["new_cat_uz"],data["new_cat_ru"],message.text.strip())
    await state.update_data(ma_category=data["new_cat_slug"])
    await state.set_state(ManualAddStates.waiting_category)
    cats = db.get_all_categories()
    await message.answer(t(lang,"cat_added",name=data["new_cat_uz"],slug=data["new_cat_slug"]),parse_mode="HTML")
    await message.answer(t(lang,"ma_ask_category"),parse_mode="HTML",reply_markup=ma_categories_keyboard(lang,cats))


# ── 3. SUBKATEGORIYA ─────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("masub:"), ManualAddStates.waiting_subcategory)
async def ma_got_subcat(callback, state):
    lang = db.get_user_lang(callback.from_user.id)
    parts = callback.data.split(":", 2)
    if parts[1] == "skip":
        await state.update_data(ma_subcategory="")
        await callback.answer()
        await _ask_format(callback.message, state, lang)
    elif parts[1] == "back":
        await callback.answer()
        cats = db.get_all_categories()
        await state.set_state(ManualAddStates.waiting_category)
        await callback.message.answer(t(lang,"ma_ask_category"),parse_mode="HTML",
                                      reply_markup=ma_categories_keyboard(lang,cats))
    else:
        await state.update_data(ma_subcategory=parts[2])
        await callback.answer()
        await _ask_format(callback.message, state, lang)

@router.callback_query(F.data.startswith("ma:newsub:"), ManualAddStates.waiting_subcategory)
async def ma_newsub_start(callback, state):
    lang = db.get_user_lang(callback.from_user.id)
    cat_slug = callback.data.split(":",2)[2]
    await state.update_data(new_sub_cat=cat_slug)
    await state.set_state(ManualAddEditStates.new_sub_slug)
    await callback.message.answer(t(lang,"sub_add_slug"),parse_mode="HTML",
                                  reply_markup=cancel_only_keyboard(lang))
    await callback.answer()

@router.message(ManualAddEditStates.new_sub_slug, F.text)
async def ma_newsub_slug(message, state):
    lang = db.get_user_lang(message.from_user.id)
    data = await state.get_data()
    slug = message.text.strip().lower()
    if not SLUG_RE.match(slug): await message.answer(t(lang,"cat_slug_invalid")); return
    if db.get_subcategory(data.get("new_sub_cat",""),slug): await message.answer(t(lang,"sub_slug_exists")); return
    await state.update_data(new_sub_slug=slug)
    await state.set_state(ManualAddEditStates.new_sub_uz)
    await message.answer(t(lang,"sub_add_uz"),parse_mode="HTML")

@router.message(ManualAddEditStates.new_sub_uz, F.text)
async def ma_newsub_uz(message, state):
    await state.update_data(new_sub_uz=message.text.strip())
    await state.set_state(ManualAddEditStates.new_sub_ru)
    await message.answer(t(db.get_user_lang(message.from_user.id),"sub_add_ru"),parse_mode="HTML")

@router.message(ManualAddEditStates.new_sub_ru, F.text)
async def ma_newsub_ru(message, state):
    await state.update_data(new_sub_ru=message.text.strip())
    await state.set_state(ManualAddEditStates.new_sub_en)
    await message.answer(t(db.get_user_lang(message.from_user.id),"sub_add_en"),parse_mode="HTML")

@router.message(ManualAddEditStates.new_sub_en, F.text)
async def ma_newsub_en(message, state):
    lang = db.get_user_lang(message.from_user.id)
    data = await state.get_data()
    cat_slug = data.get("new_sub_cat","")
    db.add_subcategory(cat_slug,data["new_sub_slug"],data["new_sub_uz"],data["new_sub_ru"],message.text.strip())
    await state.update_data(ma_subcategory=data["new_sub_slug"])
    await state.set_state(ManualAddStates.waiting_subcategory)
    subs = db.get_subcategories(cat_slug)
    await message.answer(t(lang,"sub_added",name=data["new_sub_uz"]),parse_mode="HTML")
    await message.answer(t(lang,"ma_ask_subcat"),parse_mode="HTML",
                         reply_markup=ma_subcategories_keyboard(lang,cat_slug,subs))


# ── 4. FORMAT ────────────────────────────────────────────────────────────────
async def _ask_format(msg, state, lang):
    await state.set_state(ManualAddStates.waiting_format)
    await msg.answer(t(lang,"ma_ask_format"),parse_mode="HTML",reply_markup=skip_keyboard(lang))

@router.message(ManualAddStates.waiting_format, F.text)
async def ma_got_format(message, state):
    lang = db.get_user_lang(message.from_user.id)
    await state.update_data(ma_format=message.text.strip())
    await _ask_thickness(message, state, lang)

@router.callback_query(F.data=="ma:skip", ManualAddStates.waiting_format)
async def ma_skip_format(callback, state):
    lang = db.get_user_lang(callback.from_user.id)
    await state.update_data(ma_format=""); await callback.answer()
    await _ask_thickness(callback.message, state, lang)


# ── 5. QALINLIK ──────────────────────────────────────────────────────────────
async def _ask_thickness(msg, state, lang):
    await state.set_state(ManualAddStates.waiting_thickness)
    await msg.answer(t(lang,"ma_ask_thickness"),parse_mode="HTML",reply_markup=skip_keyboard(lang))

@router.message(ManualAddStates.waiting_thickness, F.text)
async def ma_got_thickness(message, state):
    lang = db.get_user_lang(message.from_user.id)
    await state.update_data(ma_thickness=message.text.strip())
    await _ask_price(message, state, lang)

@router.callback_query(F.data=="ma:skip", ManualAddStates.waiting_thickness)
async def ma_skip_thickness(callback, state):
    lang = db.get_user_lang(callback.from_user.id)
    await state.update_data(ma_thickness=""); await callback.answer()
    await _ask_price(callback.message, state, lang)


# ── 6. NARX (majburiy) ───────────────────────────────────────────────────────
async def _ask_price(msg, state, lang):
    await state.set_state(ManualAddStates.waiting_price)
    await msg.answer(t(lang,"ma_ask_price"),parse_mode="HTML")

@router.message(ManualAddStates.waiting_price, F.text)
async def ma_got_price(message, state):
    lang = db.get_user_lang(message.from_user.id)
    try:
        price = float(message.text.strip().replace(" ","").replace(",","."))
        if price < 0: raise ValueError
    except ValueError:
        await message.answer(t(lang,"ma_price_invalid")); return
    await state.update_data(ma_price=price)
    await _ask_quantity(message, state, lang)


# ── 7. MIQDOR ────────────────────────────────────────────────────────────────
async def _ask_quantity(msg, state, lang):
    await state.set_state(ManualAddStates.waiting_quantity)
    await msg.answer(t(lang,"ma_ask_quantity"),parse_mode="HTML")

@router.message(ManualAddStates.waiting_quantity, F.text)
async def ma_got_quantity(message, state):
    lang = db.get_user_lang(message.from_user.id)
    try:
        qty = float(message.text.strip().replace(",","."))
        if qty < 0: raise ValueError
    except ValueError:
        await message.answer(t(lang,"ma_qty_invalid")); return
    await state.update_data(ma_quantity=qty)
    await state.set_state(ManualAddStates.waiting_location)
    await message.answer(t(lang,"ma_ask_location"),parse_mode="HTML",reply_markup=skip_keyboard(lang))


# ── 8. JOYLASHUV ─────────────────────────────────────────────────────────────
@router.message(ManualAddStates.waiting_location, F.text)
async def ma_got_location(message, state):
    lang = db.get_user_lang(message.from_user.id)
    await state.update_data(ma_location=message.text.strip())
    await _ask_image(message, state, lang)

@router.callback_query(F.data=="ma:skip", ManualAddStates.waiting_location)
async def ma_skip_location(callback, state):
    lang = db.get_user_lang(callback.from_user.id)
    await state.update_data(ma_location=""); await callback.answer()
    await _ask_image(callback.message, state, lang)


# ── 9. RASM ──────────────────────────────────────────────────────────────────
async def _ask_image(msg, state, lang):
    await state.set_state(ManualAddStates.waiting_image)
    await msg.answer(t(lang,"ma_ask_image"),parse_mode="HTML",reply_markup=skip_photo_keyboard(lang))

@router.message(ManualAddStates.waiting_image, F.photo)
async def ma_got_image(message, state, bot: Bot):
    lang  = db.get_user_lang(message.from_user.id)
    photo = message.photo[-1]
    fi    = await bot.get_file(photo.file_id)
    fname = f"prod_{uuid.uuid4().hex[:8]}.jpg"
    path  = os.path.join(IMAGES_DIR, fname)
    await bot.download_file(fi.file_path, destination=path)
    await state.update_data(ma_image=path)
    await _show_preview(message, state, lang)

@router.callback_query(F.data=="ma:skip_photo", ManualAddStates.waiting_image)
async def ma_skip_image(callback, state):
    lang = db.get_user_lang(callback.from_user.id)
    await state.update_data(ma_image=None); await callback.answer()
    await _show_preview(callback.message, state, lang)

@router.message(ManualAddStates.waiting_image)
async def ma_wrong_image(message):
    await message.answer(t(db.get_user_lang(message.from_user.id),"photo_invalid"))


# ── TASDIQLASH ───────────────────────────────────────────────────────────────
@router.callback_query(F.data=="ma:confirm")
async def ma_confirm(callback, state):
    if not is_admin(callback.from_user.id): await callback.answer(); return
    lang = db.get_user_lang(callback.from_user.id)
    data = await state.get_data()

    pid = db.add_product(
        name=data.get("ma_name",""), code=data.get("ma_code",""),
        category=data.get("ma_category",""), subcategory=data.get("ma_subcategory",""),
        format_size=data.get("ma_format",""), thickness=data.get("ma_thickness",""),
        quantity=data.get("ma_quantity",0), location=data.get("ma_location",""),
        image_path=data.get("ma_image"), price=data.get("ma_price",0),
    )

    # ✅ QR CODE YARATISH — mahsulot qo'shilgandan keyin
    try:
        from utils.qr_utils import generate_qr
        generate_qr(data.get("ma_code",""), pid, data.get("ma_name",""))
    except Exception:
        pass

    cat_label = db.get_category_label(lang, data.get("ma_category",""))
    await callback.message.answer(
        t(lang,"ma_done", name=data.get("ma_name",""),
          code=data.get("ma_code","") or "-",
          category=cat_label, quantity=data.get("ma_quantity",0)),
        parse_mode="HTML")

    # Rasm va QR code birga yuborish
    if data.get("ma_image") and os.path.exists(data["ma_image"]):
        try:
            from utils.qr_utils import get_or_create_qr
            from aiogram.types import FSInputFile, InputMediaPhoto
            prod = db.get_product(pid)
            qr_path = get_or_create_qr(prod)
            if qr_path and os.path.exists(qr_path):
                # Rasm va QR ni birga album sifatida yuborish
                await callback.message.answer_media_group([
                    InputMediaPhoto(
                        media=FSInputFile(data["ma_image"]),
                        caption=f"📷 {data.get('ma_name','')}"
                    ),
                    InputMediaPhoto(
                        media=FSInputFile(qr_path),
                        caption=f"📦 QR: <code>{data.get('ma_code','') or '#'+str(pid)}</code>",
                    ),
                ])
        except Exception:
            pass

    role = get_role_level(callback.from_user.id)
    await state.set_state(AdminStates.main_menu)
    await callback.message.answer(t(lang,"main_menu"),
                                  reply_markup=get_main_keyboard(lang,role))
    await callback.answer()


@router.callback_query(F.data=="ma:cancel")
async def ma_cancel(callback, state):
    lang = db.get_user_lang(callback.from_user.id)
    role = get_role_level(callback.from_user.id)
    await state.set_state(AdminStates.main_menu)
    await callback.message.answer(t(lang,"action_cancelled"),
                                  reply_markup=get_main_keyboard(lang,role))
    await callback.answer()


# ── TAHRIRLASH ───────────────────────────────────────────────────────────────
@router.callback_query(F.data=="ma:edit")
async def ma_edit_start(callback, state):
    lang = db.get_user_lang(callback.from_user.id)
    await state.set_state(ManualAddEditStates.choosing_field)
    await callback.message.answer(t(lang,"edit_choose_field"),parse_mode="HTML",
                                  reply_markup=ma_edit_fields_keyboard(lang))
    await callback.answer()

@router.callback_query(F.data.startswith("maedit:"), ManualAddEditStates.choosing_field)
async def ma_edit_field(callback, state):
    lang  = db.get_user_lang(callback.from_user.id)
    field = callback.data.split(":",1)[1]
    if field == "done":
        await state.set_state(ManualAddStates.waiting_image)
        await _show_preview(callback, state, lang)
        await callback.answer(); return
    data = await state.get_data()
    if field == "category":
        cats = db.get_all_categories()
        await state.set_state(ManualAddEditStates.editing_category)
        await callback.message.answer(t(lang,"ma_ask_category"),parse_mode="HTML",
                                      reply_markup=ma_categories_keyboard(lang,cats))
        await callback.answer(); return
    if field == "subcategory":
        cat_slug = data.get("ma_category","")
        subs = db.get_subcategories(cat_slug)
        await state.set_state(ManualAddEditStates.editing_subcategory)
        await callback.message.answer(t(lang,"ma_ask_subcat"),parse_mode="HTML",
                                      reply_markup=ma_subcategories_keyboard(lang,cat_slug,subs))
        await callback.answer(); return
    field_map = {"name":"ma_name","code":"ma_code","format":"ma_format",
                 "thickness":"ma_thickness","price":"ma_price","quantity":"ma_quantity","location":"ma_location"}
    data_key = field_map.get(field, f"ma_{field}")
    current  = data.get(data_key,"") or "-"
    await state.update_data(editing_field=field, editing_data_key=data_key)
    await state.set_state(ManualAddEditStates.editing_value)
    await callback.message.answer(t(lang,"edit_current_val",value=current),parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("macat:"), ManualAddEditStates.editing_category)
async def ma_edit_cat(callback, state):
    lang = db.get_user_lang(callback.from_user.id)
    await state.update_data(ma_category=callback.data.split(":",1)[1], ma_subcategory="")
    await state.set_state(ManualAddEditStates.choosing_field)
    await callback.message.answer(t(lang,"edit_choose_field"),parse_mode="HTML",
                                  reply_markup=ma_edit_fields_keyboard(lang))
    await callback.answer()

@router.callback_query(F.data.startswith("masub:"), ManualAddEditStates.editing_subcategory)
async def ma_edit_sub(callback, state):
    lang  = db.get_user_lang(callback.from_user.id)
    parts = callback.data.split(":",2)
    await state.update_data(ma_subcategory="" if parts[1]=="skip" else parts[2])
    await state.set_state(ManualAddEditStates.choosing_field)
    await callback.message.answer(t(lang,"edit_choose_field"),parse_mode="HTML",
                                  reply_markup=ma_edit_fields_keyboard(lang))
    await callback.answer()

@router.message(ManualAddEditStates.editing_value, F.text)
async def ma_edit_value(message, state):
    lang     = db.get_user_lang(message.from_user.id)
    data     = await state.get_data()
    field    = data.get("editing_field","")
    data_key = data.get("editing_data_key","")
    value    = message.text.strip()
    if field in ("price","quantity"):
        try: value = float(value.replace(" ","").replace(",","."))
        except: await message.answer(t(lang,"ma_price_invalid" if field=="price" else "ma_qty_invalid")); return
    await state.update_data(**{data_key: value})
    await state.set_state(ManualAddEditStates.choosing_field)
    await message.answer(t(lang,"edit_choose_field"),parse_mode="HTML",
                         reply_markup=ma_edit_fields_keyboard(lang))
