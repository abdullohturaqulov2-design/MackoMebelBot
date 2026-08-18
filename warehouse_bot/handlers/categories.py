# -*- coding: utf-8 -*-
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
def _all(k): return {TEXTS[l][k] for l in TEXTS if k in TEXTS[l]}


def _auto_slug(name: str) -> str:
    """O'zbek nomidan avtomatik slug yaratish."""
    import unicodedata
    s = unicodedata.normalize('NFKD', name.lower())
    s = re.sub(r'[^\w\s-]', '', s)
    s = re.sub(r'[\s]+', '_', s.strip())
    s = re.sub(r'[^a-z0-9_]', '', s)
    return s[:32] or f"cat_{hash(name) % 10000}"


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

@router.callback_query(F.data.startswith("cmgr:view:"))
async def cb_cat_view(callback: CallbackQuery):
    lang = db.get_user_lang(callback.from_user.id)
    slug = callback.data.split(":")[2]
    cat  = db.get_category(slug)
    if not cat: await callback.answer("Topilmadi", show_alert=True); return
    subs  = db.get_subcategories(slug)
    sub_t = "\n".join(f"  📁 {s[f'name_{lang}']}" for s in subs) if subs else t(lang,"no_subs")
    count = db.count_products_in_category(slug)
    text  = t(lang,"cat_detail", name=cat[f"name_{lang}"], slug=slug,
              count=count, subs=sub_t)
    await safe_edit_or_send(callback, text,
                            cat_mgr_detail_keyboard(lang, slug, count>0))
    await callback.answer()


# ── Yangi kategoriya (FAQAT O'ZBEK NOMI) ─────────────────────────────────────
@router.callback_query(F.data == "cmgr:addcat")
async def cb_addcat(callback: CallbackQuery, state: FSMContext):
    lang = db.get_user_lang(callback.from_user.id)
    await state.set_state(CategoryStates.adding_cat_uz)
    await callback.message.answer(
        "📂 <b>Yangi kategoriya</b>\n\n"
        "Kategoriya nomini yozing (o'zbekcha):\n"
        "<i>Misol: Akril, MDF, Laminat</i>",
        parse_mode="HTML",
        reply_markup=cancel_only_keyboard(lang))
    await callback.answer()

@router.message(CategoryStates.adding_cat_uz, F.text)
async def got_cat_uz(message: Message, state: FSMContext):
    lang = db.get_user_lang(message.from_user.id)
    uz   = message.text.strip()
    slug = _auto_slug(uz)

    if db.category_exists(slug):
        # Slug mavjud bo'lsa raqam qo'shish
        slug = f"{slug}_{len(db.get_all_categories())}"

    # Auto: ru va en = uz (tarjima so'ralmaydi)
    db.add_category(slug, uz, uz, uz)
    await state.set_state(AdminStates.cat_mgr)
    cats = db.get_all_categories()
    await message.answer(
        t(lang,"cat_added", name=uz, slug=slug),
        parse_mode="HTML")
    await message.answer(t(lang,"cat_mgr_title"), parse_mode="HTML",
                         reply_markup=cat_mgr_list_keyboard(lang, cats))


# ── Kategoriyani o'chirish ────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("cmgr:delcat:"))
async def cb_delcat(callback: CallbackQuery):
    lang  = db.get_user_lang(callback.from_user.id)
    slug  = callback.data.split(":")[2]
    cat   = db.get_category(slug)
    if not cat: await callback.answer(); return
    count = db.count_products_in_category(slug)
    if count > 0:
        await callback.answer(t(lang,"cat_delete_has_prods",count=count),show_alert=True); return
    await safe_edit_or_send(callback,
        t(lang,"confirm_del_cat", name=cat[f"name_{lang}"]),
        confirm_keyboard(lang, f"cmgr:delcat_yes:{slug}"))
    await callback.answer()

@router.callback_query(F.data.startswith("cmgr:delcat_yes:"))
async def cb_delcat_yes(callback: CallbackQuery, state: FSMContext):
    lang = db.get_user_lang(callback.from_user.id)
    slug = callback.data.split(":")[2]
    cat  = db.get_category(slug)
    name = cat[f"name_{lang}"] if cat else slug
    db.delete_category(slug)
    cats = db.get_all_categories()
    await safe_edit_or_send(callback,
        t(lang,"cat_deleted",name=name)+"\n\n"+t(lang,"cat_mgr_title"),
        cat_mgr_list_keyboard(lang, cats))
    await callback.answer(t(lang,"cat_deleted",name=name), show_alert=True)


# ── Yangi subkategoriya (FAQAT O'ZBEK NOMI) ──────────────────────────────────
@router.callback_query(F.data.startswith("cmgr:addsub:"))
async def cb_addsub(callback: CallbackQuery, state: FSMContext):
    lang     = db.get_user_lang(callback.from_user.id)
    cat_slug = callback.data.split(":")[2]
    await state.update_data(sub_cat_slug=cat_slug)
    await state.set_state(CategoryStates.adding_sub_uz)
    await callback.message.answer(
        "📁 <b>Yangi subkategoriya</b>\n\n"
        "Subkategoriya nomini yozing (o'zbekcha):",
        parse_mode="HTML",
        reply_markup=cancel_only_keyboard(lang))
    await callback.answer()

@router.message(CategoryStates.adding_sub_uz, F.text)
async def got_sub_uz(message: Message, state: FSMContext):
    lang     = db.get_user_lang(message.from_user.id)
    data     = await state.get_data()
    cat_slug = data.get("sub_cat_slug","")
    uz       = message.text.strip()
    slug     = _auto_slug(uz)

    if db.get_subcategory(cat_slug, slug):
        slug = f"{slug}_{len(db.get_subcategories(cat_slug))}"

    db.add_subcategory(cat_slug, slug, uz, uz, uz)
    await state.set_state(AdminStates.cat_mgr)
    subs = db.get_subcategories(cat_slug)
    await message.answer(t(lang,"sub_added",name=uz), parse_mode="HTML")
    await message.answer(t(lang,"cat_mgr_title"), parse_mode="HTML",
                         reply_markup=cat_mgr_list_keyboard(lang, db.get_all_categories()))


# ── Subkategoriya o'chirish ───────────────────────────────────────────────────
@router.callback_query(F.data.startswith("cmgr:delsub:"))
async def cb_delsub(callback: CallbackQuery):
    lang     = db.get_user_lang(callback.from_user.id)
    parts    = callback.data.split(":", 3)
    cat_slug = parts[2]; sub_slug = parts[3]
    sub   = db.get_subcategory(cat_slug, sub_slug)
    if not sub: await callback.answer(); return
    count = db.count_products_in_subcategory(cat_slug, sub_slug)
    if count > 0:
        await callback.answer(t(lang,"sub_delete_has_prods",count=count),show_alert=True); return
    await safe_edit_or_send(callback,
        t(lang,"confirm_del_sub",name=sub[f"name_{lang}"]),
        confirm_keyboard(lang, f"cmgr:delsub_yes:{cat_slug}:{sub_slug}"))
    await callback.answer()

@router.callback_query(F.data.startswith("cmgr:delsub_yes:"))
async def cb_delsub_yes(callback: CallbackQuery):
    lang     = db.get_user_lang(callback.from_user.id)
    parts    = callback.data.split(":", 3)
    cat_slug = parts[2]; sub_slug = parts[3]
    sub      = db.get_subcategory(cat_slug, sub_slug)
    name     = sub[f"name_{lang}"] if sub else sub_slug
    db.delete_subcategory(cat_slug, sub_slug)
    await safe_edit_or_send(callback, t(lang,"sub_deleted",name=name))
    await callback.answer(t(lang,"sub_deleted",name=name), show_alert=True)
