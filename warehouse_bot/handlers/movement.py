# -*- coding: utf-8 -*-
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from database import db
from locales.texts import TEXTS, t
from keyboards.reply import cancel_only_keyboard, get_main_keyboard
from keyboards.inline import (mv_type_keyboard, mv_note_keyboard,
                               products_list_keyboard, product_detail_back_keyboard, paginate)
from states.states import AdminStates, MovementStates
from utils.access import is_admin, get_role_level
from utils.render import delete_msg
from utils.render import send_products_list, send_product_detail
from utils.cache import SEARCH_CACHE

router = Router()

def _all(key): return {TEXTS[l][key] for l in TEXTS}

# ── Asosiy menyu tugmasi ─────────────────────────────────────────────────────
@router.message(F.text.in_(_all("btn_movement")))
async def start_movement(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await delete_msg(message)
    lang = db.get_user_lang(message.from_user.id)
    await state.set_state(MovementStates.searching)
    await message.answer(t(lang,"mv_search_prompt"), reply_markup=cancel_only_keyboard(lang))

# ── Mahsulot qidirish ────────────────────────────────────────────────────────
@router.message(MovementStates.searching, F.text)
async def mv_search(message: Message, state: FSMContext):
    lang = db.get_user_lang(message.from_user.id)
    q    = message.text.strip()
    rows = db.search_by_name(q) or db.search_by_code(q)
    if not rows:
        await message.answer(t(lang,"product_not_found")); return
    if len(rows) == 1:
        # bitta topilsa bevosita harakat tanlashga o'tamiz
        prod = rows[0]
        await state.update_data(prod_id=prod["id"], prod_name=prod["name"],
                                 prod_qty=prod["quantity"], back_cb="mv_back")
        await state.set_state(MovementStates.choosing_type)
        await message.answer(
            t(lang,"mv_choose_type", name=prod["name"]),
            reply_markup=mv_type_keyboard(lang), parse_mode="HTML")
        return
    SEARCH_CACHE[message.from_user.id] = {"field":"name","value":q}
    await send_products_list(message, lang, rows, 0,
        item_prefix="mvsel:0", nav_prefix="mvsrch",
        title_key="search_results_title")

@router.callback_query(F.data.startswith("mvsrch:"))
async def cb_mvsrch(callback: CallbackQuery):
    lang  = db.get_user_lang(callback.from_user.id)
    page  = int(callback.data.split(":")[1])
    cache = SEARCH_CACHE.get(callback.from_user.id, {})
    q     = cache.get("value","")
    rows  = db.search_by_name(q) or db.search_by_code(q)
    await send_products_list(callback, lang, rows, page,
        item_prefix=f"mvsel:{page}", nav_prefix="mvsrch",
        title_key="search_results_title", edit=True)
    await callback.answer()

@router.callback_query(F.data.startswith("mvsel:"))
async def cb_mvsel(callback: CallbackQuery, state: FSMContext):
    lang = db.get_user_lang(callback.from_user.id)
    _, page_str, pid = callback.data.split(":", 2)
    prod = db.get_product(int(pid))
    if not prod: await callback.answer(); return
    await state.update_data(prod_id=prod["id"], prod_name=prod["name"],
                             prod_qty=prod["quantity"], back_cb=f"mvsrch:{page_str}")
    await state.set_state(MovementStates.choosing_type)
    await callback.message.answer(
        t(lang,"mv_choose_type", name=prod["name"]),
        reply_markup=mv_type_keyboard(lang), parse_mode="HTML")
    await callback.answer()

# ── Mahsulot detail dan bevosita kirim/chiqim ────────────────────────────────
@router.callback_query(F.data.startswith("mvf:"))
async def cb_mvf(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): await callback.answer(); return
    lang = db.get_user_lang(callback.from_user.id)
    _, mv_type, pid = callback.data.split(":", 2)
    prod = db.get_product(int(pid))
    if not prod: await callback.answer(); return
    await state.update_data(prod_id=prod["id"], prod_name=prod["name"],
                             prod_qty=prod["quantity"], mv_type=mv_type,
                             back_cb=f"catshow")
    await state.set_state(MovementStates.entering_qty)
    await callback.message.answer(t(lang,"mv_enter_qty"))
    await callback.answer()

# ── Harakat turi tanlash (inline) ────────────────────────────────────────────
@router.callback_query(F.data.startswith("mv:"), MovementStates.choosing_type)
async def cb_mv_type(callback: CallbackQuery, state: FSMContext):
    lang    = db.get_user_lang(callback.from_user.id)
    mv_type = callback.data.split(":")[1]
    await state.update_data(mv_type=mv_type)
    await state.set_state(MovementStates.entering_qty)
    await callback.message.answer(t(lang,"mv_enter_qty"))
    await callback.answer()

# ── Miqdor kiritish ──────────────────────────────────────────────────────────
@router.message(MovementStates.entering_qty, F.text)
async def mv_enter_qty(message: Message, state: FSMContext):
    lang = db.get_user_lang(message.from_user.id)
    try:
        qty = float(message.text.strip().replace(",","."))
        if qty <= 0: raise ValueError
    except ValueError:
        await message.answer(t(lang,"mv_invalid_qty")); return

    data = await state.get_data()
    if data.get("mv_type") == "OUT" and data.get("prod_qty",0) < qty:
        await message.answer(t(lang,"mv_not_enough", qty=data["prod_qty"]), parse_mode="HTML"); return

    await state.update_data(mv_qty=qty)
    await state.set_state(MovementStates.entering_note)
    await message.answer(t(lang,"mv_enter_note"), reply_markup=mv_note_keyboard(lang))

# ── Izoh (yoki o'tkazib yuborish) ───────────────────────────────────────────
@router.message(MovementStates.entering_note, F.text)
async def mv_enter_note(message: Message, state: FSMContext, bot: Bot):
    lang = db.get_user_lang(message.from_user.id)
    note = message.text.strip()
    await _complete_movement(message, state, bot, lang, note)

@router.callback_query(F.data == "mv:skip_note", MovementStates.entering_note)
async def mv_skip_note(callback: CallbackQuery, state: FSMContext, bot: Bot):
    lang = db.get_user_lang(callback.from_user.id)
    await callback.answer()
    await _complete_movement(callback.message, state, bot, lang, "")

async def _complete_movement(msg, state: FSMContext, bot: Bot, lang: str, note: str):
    data      = await state.get_data()
    prod_id   = data["prod_id"]
    mv_type   = data["mv_type"]
    qty       = data["mv_qty"]
    uid       = msg.chat.id
    user      = await bot.get_chat(uid)
    admin_name= user.full_name or str(uid)

    prod    = db.get_product(prod_id)
    cur_qty = prod["quantity"]
    new_qty = cur_qty + qty if mv_type == "IN" else cur_qty - qty
    new_qty = max(0, new_qty)

    db.update_product_quantity(prod_id, new_qty)
    db.record_movement(prod_id, mv_type, qty, note, uid, admin_name)

    key     = "mv_done_in" if mv_type == "IN" else "mv_done_out"
    await msg.answer(t(lang, key, qty=qty, new_qty=new_qty), parse_mode="HTML")

    # Kam qoldi ogohlantirishini yuborish
    prod = db.get_product(prod_id)
    min_q = prod["min_quantity"] or 0
    if mv_type == "OUT" and min_q > 0 and new_qty < min_q:
        alert = t(lang,"mv_low_alert", name=prod["name"],
                  qty=new_qty, min_qty=min_q,
                  location=prod["location"] or "-")
        admin_ids = db.get_all_notifiable_admin_ids()
        for aid in admin_ids:
            try: await bot.send_message(aid, alert, parse_mode="HTML")
            except: pass

    role = get_role_level(uid)
    from keyboards.reply import get_main_keyboard
    await msg.answer(t(lang,"main_menu"), reply_markup=get_main_keyboard(lang, role))
    await state.set_state(AdminStates.main_menu)

# ── Min miqdor belgilash (product detail dan) ────────────────────────────────
@router.callback_query(F.data.startswith("mvmq:"))
async def cb_mvmq(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): await callback.answer(); return
    lang = db.get_user_lang(callback.from_user.id)
    pid  = int(callback.data.split(":")[1])
    prod = db.get_product(pid)
    if not prod: await callback.answer(); return
    await state.update_data(minqty_prod_id=pid)
    await state.set_state(MovementStates.setting_min)
    await callback.message.answer(
        t(lang,"mv_set_min_prompt", current=prod["min_quantity"] or 0),
        parse_mode="HTML")
    await callback.answer()

@router.message(MovementStates.setting_min, F.text)
async def mv_set_min(message: Message, state: FSMContext):
    lang = db.get_user_lang(message.from_user.id)
    try:
        val = float(message.text.strip().replace(",","."))
        if val < 0: raise ValueError
    except ValueError:
        await message.answer(t(lang,"mv_invalid_qty")); return
    data = await state.get_data()
    db.set_min_quantity(data["minqty_prod_id"], val)
    await message.answer(t(lang,"mv_min_set", qty=val), parse_mode="HTML")
    role = get_role_level(message.from_user.id)
    from keyboards.reply import get_main_keyboard
    await message.answer(t(lang,"main_menu"), reply_markup=get_main_keyboard(lang, role))
    await state.set_state(AdminStates.main_menu)

# ── Harakat tarixi ───────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("mvh:"))
async def cb_mvh(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer(); return
    lang = db.get_user_lang(callback.from_user.id)
    pid  = int(callback.data.split(":")[1])
    prod = db.get_product(pid)
    if not prod: await callback.answer(); return
    movs = db.get_product_movements(pid, limit=30)
    from keyboards.inline import product_detail_back_keyboard
    kb   = product_detail_back_keyboard(lang, f"catshow")
    if not movs:
        await callback.message.answer(
            t(lang,"mv_history_title",name=prod["name"]) + t(lang,"mv_no_history"),
            reply_markup=kb, parse_mode="HTML")
        await callback.answer(); return
    lines = ""
    for m in movs:
        emoji = "📥" if m["movement_type"]=="IN" else "📤"
        mtype = "Kirim" if m["movement_type"]=="IN" else "Chiqim"
        lines += t(lang,"mv_hist_entry",
                   emoji=emoji, mv_type=mtype,
                   qty=m["quantity"],
                   admin=m["admin_name"] or str(m["admin_id"]),
                   date=m["created_at"][:16],
                   note=m["note"] or "-")
    text = t(lang,"mv_history_title",name=prod["name"]) + lines
    await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()
