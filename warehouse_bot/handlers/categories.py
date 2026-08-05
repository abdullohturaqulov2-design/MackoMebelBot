# -*- coding: utf-8 -*-
"""
Kategoriya va subkategoriya boshqaruvi.
O'chirish, qo'shish hammasini qamrab oladi.
"""
import re
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import db
from locales.texts import TEXTS, t
from keyboards.inline import (cat_mgr_list_keyboard, cat_mgr_detail_keyboard,
                               sub_mgr_detail_keyboard, confirm_keyboard)
from keyboards.reply import cancel_only_keyboard, get_main_keyboard
from states.states import AdminStates, CategoryStates
from utils.access import is_admin, get_role_level
from utils.render import delete_msg, safe_edit_or_send

router  = Router()
SLUG_RE = re.compile(r'^[a-zA-Z0-9_]{1,32}$')
def _all(k): return {TEXTS[l][k] for l in TEXTS}


# ── Ochish ────────────────────────────────────────────────────────────────────
@router.message(F.text.in_(_all("btn_manage_cats")))
async def open_cat_mgr(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await delete_msg(message)
    lang = db.get_user_lang(message.from_user.id)
    cats = db.get_all_categories()
    await state.set_state(AdminStates.cat_mgr)
    await message.answer(t(lang,"cat_mgr_title"), parse_mode="HTML",
                         reply_markup=cat_mgr_list_keyboard(lang, cats))


@router.callback_query(F.data == "cmgr:list")
async def cb_cat_list(callback: CallbackQuery, state: FSMContext):
    lang = db.get_user_lang(callback.from_user.id)
    cats = db.get_all_categories()
    await state.set_state(AdminStates.cat_mgr)
    await safe_edit_or_send(callback, t(lang,"cat_mgr_title"),
                            cat_mgr_list_keyboard(lang, cats))
    await callback.answer()


# ── Kategoriya detail ─────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("cmgr:view:"))
async def cb_cat_view(callback: CallbackQuery, state: FSMContext):
    lang = db.get_user_lang(callback.from_user.id)
    slug = callback.data.split(":")[2]
    cat  = db.get_category(slug)
    if not cat: await callback.answer("Topilmadi", show_alert=True); return

    subs = db.get_subcategories(slug)
    sub_text = "\n".join(
        f"  📁 {s[f'name_{lang}']}" for s in subs
    ) if subs else t(lang,"no_subs")

    count = db.count_products_in_category(slug)
    text  = t(lang,"cat_detail",
              name=cat[f"name_{lang}"], slug=slug,
              count=count, subs=sub_text)

    await safe_edit_or_send(callback, text,
                            cat_mgr_detail_keyboard(lang, slug, count>0))
    await callback.answer()


# ── Yangi kategoriya ──────────────────────────────────────────────────────────
@router.callback_query(F.data == "cmgr:addcat")
async def cb_addcat_start(callback: CallbackQuery, state: FSMContext):
    lang = db.get_user_lang(callback.from_user.id)
    await state.set_state(CategoryStates.adding_cat_slug)
    await callback.message.answer(t(lang,"cat_add_slug"), parse_mode="HTML",
                                  reply_markup=cancel_only_keyboard(lang))
    await callback.answer()

@router.message(CategoryStates.adding_cat_slug, F.text)
async def got_cat_slug(message: Message, state: FSMContext):
    lang = db.get_user_lang(message.from_user.id)
    slug = message.text.strip().lower()
    if not SLUG_RE.match(slug):
        await message.answer(t(lang,"cat_slug_invalid")); return
    if db.category_exists(slug):
        await message.answer(t(lang,"cat_slug_exists")); return
    await state.update_data(cat_slug=slug)
    await state.set_state(CategoryStates.adding_cat_uz)
    await message.answer(t(lang,"cat_add_uz"), parse_mode="HTML")

@router.message(CategoryStates.adding_cat_uz, F.text)
async def got_cat_uz(message: Message, state: FSMContext):
    await state.update_data(cat_uz=message.text.strip())
    await state.set_state(CategoryStates.adding_cat_ru)
    lang = db.get_user_lang(message.from_user.id)
    await message.answer(t(lang,"cat_add_ru"), parse_mode="HTML")

@router.message(CategoryStates.adding_cat_ru, F.text)
async def got_cat_ru(message: Message, state: FSMContext):
    await state.update_data(cat_ru=message.text.strip())
    await state.set_state(CategoryStates.adding_cat_en)
    lang = db.get_user_lang(message.from_user.id)
    await message.answer(t(lang,"cat_add_en"), parse_mode="HTML")

@router.message(CategoryStates.adding_cat_en, F.text)
async def got_cat_en(message: Message, state: FSMContext):
    lang = db.get_user_lang(message.from_user.id)
    data = await state.get_data()
    db.add_category(data["cat_slug"], data["cat_uz"], data["cat_ru"], message.text.strip())
    await state.set_state(AdminStates.cat_mgr)
    cats = db.get_all_categories()
    await message.answer(
        t(lang,"cat_added", name=data["cat_uz"], slug=data["cat_slug"]),
        parse_mode="HTML")
    await message.answer(t(lang,"cat_mgr_title"), parse_mode="HTML",
                         reply_markup=cat_mgr_list_keyboard(lang, cats))


# ── Kategoriyani O'CHIRISH ────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("cmgr:delcat:"))
async def cb_delcat_ask(callback: CallbackQuery, state: FSMContext):
    lang = db.get_user_lang(callback.from_user.id)
    slug = callback.data.split(":")[2]
    cat  = db.get_category(slug)
    if not cat: await callback.answer(); return
    count = db.count_products_in_category(slug)
    if count > 0:
        await callback.answer(
            t(lang,"cat_delete_has_prods", count=count), show_alert=True)
        return
    await safe_edit_or_send(
        callback,
        t(lang,"confirm_del_cat", name=cat[f"name_{lang}"]),
        confirm_keyboard(lang, f"cmgr:delcat_yes:{slug}")
    )
    await callback.answer()

@router.callback_query(F.data.startswith("cmgr:delcat_yes:"))
async def cb_delcat_confirm(callback: CallbackQuery, state: FSMContext):
    lang = db.get_user_lang(callback.from_user.id)
    slug = callback.data.split(":")[2]
    cat  = db.get_category(slug)
    name = cat[f"name_{lang}"] if cat else slug
    ok   = db.delete_category(slug)
    if not ok:
        await callback.answer("O'chirib bo'lmadi (mahsulotlar bor)", show_alert=True)
        return
    cats = db.get_all_categories()
    await safe_edit_or_send(
        callback,
        t(lang,"cat_deleted", name=name) + "\n\n" + t(lang,"cat_mgr_title"),
        cat_mgr_list_keyboard(lang, cats)
    )
    await callback.answer(t(lang,"cat_deleted", name=name), show_alert=True)


# ── Yangi subkategoriya ───────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("cmgr:addsub:"))
async def cb_addsub_start(callback: CallbackQuery, state: FSMContext):
    lang     = db.get_user_lang(callback.from_user.id)
    cat_slug = callback.data.split(":")[2]
    await state.update_data(sub_cat_slug=cat_slug)
    await state.set_state(CategoryStates.adding_sub_slug)
    await callback.message.answer(t(lang,"sub_add_slug"), parse_mode="HTML",
                                  reply_markup=cancel_only_keyboard(lang))
    await callback.answer()

@router.message(CategoryStates.adding_sub_slug, F.text)
async def got_sub_slug(message: Message, state: FSMContext):
    lang = db.get_user_lang(message.from_user.id)
    data = await state.get_data()
    slug = message.text.strip().lower()
    if not SLUG_RE.match(slug):
        await message.answer(t(lang,"cat_slug_invalid")); return
    if db.get_subcategory(data.get("sub_cat_slug",""), slug):
        await message.answer(t(lang,"sub_slug_exists")); return
    await state.update_data(sub_slug=slug)
    await state.set_state(CategoryStates.adding_sub_uz)
    await message.answer(t(lang,"sub_add_uz"), parse_mode="HTML")

@router.message(CategoryStates.adding_sub_uz, F.text)
async def got_sub_uz(message: Message, state: FSMContext):
    await state.update_data(sub_uz=message.text.strip())
    await state.set_state(CategoryStates.adding_sub_ru)
    lang = db.get_user_lang(message.from_user.id)
    await message.answer(t(lang,"sub_add_ru"), parse_mode="HTML")

@router.message(CategoryStates.adding_sub_ru, F.text)
async def got_sub_ru(message: Message, state: FSMContext):
    await state.update_data(sub_ru=message.text.strip())
    await state.set_state(CategoryStates.adding_sub_en)
    lang = db.get_user_lang(message.from_user.id)
    await message.answer(t(lang,"sub_add_en"), parse_mode="HTML")

@router.message(CategoryStates.adding_sub_en, F.text)
async def got_sub_en(message: Message, state: FSMContext):
    lang = db.get_user_lang(message.from_user.id)
    data = await state.get_data()
    cat_slug = data.get("sub_cat_slug","")
    db.add_subcategory(cat_slug, data["sub_slug"],
                       data["sub_uz"], data["sub_ru"], message.text.strip())
    await state.set_state(AdminStates.cat_mgr)
    await message.answer(t(lang,"sub_added", name=data["sub_uz"]), parse_mode="HTML")
    # Kategoriya detailiga qaytish
    cats = db.get_all_categories()
    await message.answer(t(lang,"cat_mgr_title"), parse_mode="HTML",
                         reply_markup=cat_mgr_list_keyboard(lang, cats))


# ── Subkategoriyani O'CHIRISH ─────────────────────────────────────────────────
@router.callback_query(F.data.startswith("cmgr:delsub:"))
async def cb_delsub_ask(callback: CallbackQuery, state: FSMContext):
    lang     = db.get_user_lang(callback.from_user.id)
    _, _, cat_slug, sub_slug = callback.data.split(":", 3)
    sub   = db.get_subcategory(cat_slug, sub_slug)
    if not sub: await callback.answer(); return
    count = db.count_products_in_subcategory(cat_slug, sub_slug)
    if count > 0:
        await callback.answer(
            t(lang,"sub_delete_has_prods", count=count), show_alert=True)
        return
    await safe_edit_or_send(
        callback,
        t(lang,"confirm_del_sub", name=sub[f"name_{lang}"]),
        confirm_keyboard(lang, f"cmgr:delsub_yes:{cat_slug}:{sub_slug}")
    )
    await callback.answer()

@router.callback_query(F.data.startswith("cmgr:delsub_yes:"))
async def cb_delsub_confirm(callback: CallbackQuery, state: FSMContext):
    lang = db.get_user_lang(callback.from_user.id)
    parts    = callback.data.split(":", 3)
    cat_slug = parts[2]; sub_slug = parts[3]
    sub      = db.get_subcategory(cat_slug, sub_slug)
    name     = sub[f"name_{lang}"] if sub else sub_slug
    ok       = db.delete_subcategory(cat_slug, sub_slug)
    if not ok:
        await callback.answer("O'chirib bo'lmadi (mahsulotlar bor)", show_alert=True)
        return
    subs = db.get_subcategories(cat_slug)
    await safe_edit_or_send(
        callback,
        t(lang,"sub_deleted", name=name),
        sub_mgr_detail_keyboard(lang, cat_slug, subs)
    )
    await callback.answer(t(lang,"sub_deleted", name=name), show_alert=True)
