# -*- coding: utf-8 -*-
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import db
from locales.texts import t
from keyboards.reply import get_main_keyboard
from keyboards.inline import md_confirm_keyboard, md_search_keyboard
from states.states import AdminStates, ManualDelStates
from utils.access import is_admin, get_role_level

router = Router()


async def start_manual_delete(message: Message, state: FSMContext, query: str):
    """delete_products.py dan chaqiriladi."""
    lang = db.get_user_lang(message.from_user.id)
    await _search_and_show(message, state, lang, query)


async def _search_and_show(msg, state, lang, query):
    # Avval kod bo'yicha, keyin nom bo'yicha
    rows = db.search_by_code(query)
    if not rows:
        rows = db.search_by_name(query)

    if not rows:
        await msg.answer(t(lang, "md_not_found", query=query), parse_mode="HTML")
        await state.set_state(AdminStates.main_menu)
        role = get_role_level(msg.chat.id)
        await msg.answer(t(lang,"main_menu"), reply_markup=get_main_keyboard(lang, role))
        return

    if len(rows) == 1:
        prod = rows[0]
        await _show_confirm(msg, state, lang, prod)
    else:
        await state.set_state(ManualDelStates.searching)
        await msg.answer(t(lang, "md_found_many"),
                         reply_markup=md_search_keyboard(lang, rows))


async def _show_confirm(msg, state, lang, prod):
    cat_label = db.get_category_label(lang, prod["category"])
    text = t(lang, "md_confirm",
             name    = prod["name"],
             code    = prod["code"] or "-",
             category= cat_label,
             quantity= prod["quantity"])
    await state.set_state(ManualDelStates.confirming)
    await msg.answer(text, parse_mode="HTML",
                     reply_markup=md_confirm_keyboard(lang, prod["id"]))


# ── Bir nechta natijadan tanlash ─────────────────────────────────────────────
@router.callback_query(F.data.startswith("md:sel:"), ManualDelStates.searching)
async def md_selected(callback: CallbackQuery, state: FSMContext):
    lang = db.get_user_lang(callback.from_user.id)
    pid  = int(callback.data.split(":", 2)[2])
    prod = db.get_product(pid)
    if not prod:
        await callback.answer(t(lang,"product_not_found"), show_alert=True); return
    await callback.answer()
    await _show_confirm(callback.message, state, lang, prod)


# ── O'chirish bekor ───────────────────────────────────────────────────────────
@router.callback_query(F.data == "md:cancel")
async def md_cancel(callback: CallbackQuery, state: FSMContext):
    lang = db.get_user_lang(callback.from_user.id)
    role = get_role_level(callback.from_user.id)
    await state.set_state(AdminStates.main_menu)
    await callback.message.answer(t(lang,"action_cancelled"),
                                  reply_markup=get_main_keyboard(lang, role))
    await callback.answer()


# ── O'chirishni tasdiqlash ────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("md:confirm:"), ManualDelStates.confirming)
async def md_confirmed(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): await callback.answer(); return
    lang = db.get_user_lang(callback.from_user.id)
    pid  = int(callback.data.split(":", 2)[2])
    prod = db.get_product(pid)
    if not prod:
        await callback.answer(t(lang,"product_not_found"), show_alert=True); return

    # O'chirish (kod orqali)
    code = prod["code"] or ""
    name = prod["name"]
    if code:
        db.delete_product_by_code(code)
    else:
        # Kodsiz mahsulotni ID bo'yicha o'chirish
        conn = db.get_conn(); c = conn.cursor()
        c.execute("DELETE FROM products WHERE id=?", (pid,))
        conn.commit(); conn.close()

    await callback.message.answer(t(lang,"md_done", name=name), parse_mode="HTML")
    role = get_role_level(callback.from_user.id)
    await state.set_state(AdminStates.main_menu)
    await callback.message.answer(t(lang,"main_menu"),
                                  reply_markup=get_main_keyboard(lang, role))
    await callback.answer()
