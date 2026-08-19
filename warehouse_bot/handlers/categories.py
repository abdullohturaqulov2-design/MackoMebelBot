# -*- coding: utf-8 -*-
"""
Ichma-ich kategoriya boshqaruvi.
Har qanday darajada subkategoriya qo'shish va ko'rish.
Bu fayl handlers/categories.py ni TO'LIQ ALMASHTIRADI.
"""
import re
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from database import db
from locales.texts import TEXTS, t
from keyboards.reply import cancel_only_keyboard, get_main_keyboard
from states.states import AdminStates, CategoryStates
from utils.access import is_admin, get_role_level
from utils.render import delete_msg, safe_edit_or_send

router = Router()

def _all(k): return {TEXTS[l][k] for l in TEXTS if k in TEXTS[l]}

def _slug(name: str) -> str:
    import unicodedata
    s = unicodedata.normalize('NFKD', name.lower())
    s = re.sub(r'[^\w\s]', '', s)
    s = re.sub(r'\s+', '_', s.strip())
    s = re.sub(r'[^a-z0-9_]', '', s)
    return s[:28] or f"cat_{abs(hash(name)) % 9999}"


def _cat_list_kb(lang, cats):
    b = InlineKeyboardBuilder()
    for c in cats:
        cnt = db.count_products_in_category(c["slug"])
        b.button(text=f"📂 {c[f'name_{lang}']} ({cnt})",
                 callback_data=f"cmgr:view:{c['slug']}")
    b.adjust(1)
    b.row(InlineKeyboardButton(text="➕ Yangi kategoriya",
                               callback_data="cmgr:addcat"),
          InlineKeyboardButton(text="🏠 Asosiy", callback_data="to_main"))
    return b.as_markup()


def _sub_list_kb(lang, cat_slug, subs, parent_id=None):
    """Bir daraja subkategoriyalarni ko'rsatadi."""
    b = InlineKeyboardBuilder()
    for s in subs:
        has_ch = db.has_children(s["id"])
        icon   = "📁" if has_ch else "📄"
        cnt    = db.count_products_in_subcategory(cat_slug, s["slug"])
        label  = f"{icon} {s[f'name_{lang}']} ({cnt})"
        b.button(text=label, callback_data=f"cmgr:sub:{cat_slug}:{s['id']}")
    b.adjust(1)

    # Yangi subkategoriya qo'shish (shu darajaga)
    add_cb = (f"cmgr:addsub:{cat_slug}:{parent_id}"
              if parent_id else f"cmgr:addsub:{cat_slug}:0")
    b.row(InlineKeyboardButton(text="➕ Yangi subkategoriya", callback_data=add_cb))

    # Ortga
    if parent_id:
        # Ota subkategoriyaga qaytish
        b.row(InlineKeyboardButton(text="🔙 Ortga",
                                   callback_data=f"cmgr:back_sub:{cat_slug}:{parent_id}"),
              InlineKeyboardButton(text="🗑 O'chirish",
                                   callback_data=f"cmgr:delcat:{cat_slug}"))
    else:
        b.row(InlineKeyboardButton(text="🔙 Kategoriyalar", callback_data="cmgr:list"),
              InlineKeyboardButton(text="🗑 O'chirish",
                                   callback_data=f"cmgr:delcat:{cat_slug}"))
    return b.as_markup()


# ── Ochish ────────────────────────────────────────────────────────────────────
@router.message(F.text.in_(_all("btn_manage_cats")))
async def open_cat_mgr(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await delete_msg(message)
    lang = db.get_user_lang(message.from_user.id)
    await state.set_state(AdminStates.cat_mgr)
    cats = db.get_all_categories()
    await message.answer(
        "📂 <b>Kategoriyalar boshqaruvi</b>",
        parse_mode="HTML",
        reply_markup=_cat_list_kb(lang, cats))


@router.callback_query(F.data == "cmgr:list")
async def cb_cat_list(callback: CallbackQuery, state: FSMContext):
    lang = db.get_user_lang(callback.from_user.id)
    cats = db.get_all_categories()
    await state.set_state(AdminStates.cat_mgr)
    await safe_edit_or_send(callback,
        "📂 <b>Kategoriyalar boshqaruvi</b>",
        _cat_list_kb(lang, cats))
    await callback.answer()


# ── Kategoriya ko'rish → subcategorylar ──────────────────────────────────────
@router.callback_query(F.data.startswith("cmgr:view:"))
async def cb_cat_view(callback: CallbackQuery, state: FSMContext):
    lang     = db.get_user_lang(callback.from_user.id)
    cat_slug = callback.data.split(":")[2]
    cat      = db.get_category(cat_slug)
    if not cat: await callback.answer("Topilmadi", show_alert=True); return

    # Top-level subcategorylar (parent_id IS NULL)
    subs = db.get_children(cat_slug, parent_id=None)
    cnt  = db.count_products_in_category(cat_slug)

    text = (f"📂 <b>{cat[f'name_{lang}']}</b>\n"
            f"📊 Jami mahsulot: {cnt} ta\n"
            f"📁 Subkategoriyalar: {len(subs)} ta")

    await safe_edit_or_send(callback, text,
                            _sub_list_kb(lang, cat_slug, subs))
    await callback.answer()


# ── Subkategoriya ko'rish → uning bolalari ───────────────────────────────────
@router.callback_query(F.data.startswith("cmgr:sub:"))
async def cb_sub_view(callback: CallbackQuery, state: FSMContext):
    lang     = db.get_user_lang(callback.from_user.id)
    parts    = callback.data.split(":")
    cat_slug = parts[2]
    sub_id   = int(parts[3])

    # Subcategoryni topish
    conn = db.get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM subcategories WHERE id=?", (sub_id,))
    sub = c.fetchone(); conn.close()
    if not sub: await callback.answer("Topilmadi", show_alert=True); return

    # Bolalarini olish
    children = db.get_children(cat_slug, parent_id=sub_id)

    # Breadcrumb
    path = db.get_sub_path(sub_id)
    breadcrumb = " → ".join(s[f"name_{lang}"] for s in path)
    cnt  = db.count_products_in_subcategory(cat_slug, sub["slug"])

    text = (f"📁 <b>{breadcrumb}</b>\n"
            f"📊 Mahsulotlar: {cnt} ta\n"
            f"📁 Alt-kategoriyalar: {len(children)} ta")

    if children:
        # Bolalarni ko'rsat
        await safe_edit_or_send(callback, text,
                                _sub_list_kb(lang, cat_slug, children, sub_id))
    else:
        # Bola yo'q — mahsulotlar + subkategoriya qo'shish
        b = InlineKeyboardBuilder()
        b.row(InlineKeyboardButton(text="➕ Alt-kategoriya qo'shish",
                                   callback_data=f"cmgr:addsub:{cat_slug}:{sub_id}"))
        b.row(InlineKeyboardButton(text="🗑 O'chirish",
                                   callback_data=f"cmgr:delsub:{cat_slug}:{sub['slug']}"))
        b.row(InlineKeyboardButton(text="🔙 Ortga",
                                   callback_data=f"cmgr:back_sub:{cat_slug}:{sub_id}"))
        await safe_edit_or_send(callback, text, b.as_markup())
    await callback.answer()


# ── Ortga (sub ichida) ────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("cmgr:back_sub:"))
async def cb_back_sub(callback: CallbackQuery, state: FSMContext):
    lang     = db.get_user_lang(callback.from_user.id)
    parts    = callback.data.split(":")
    cat_slug = parts[2]
    sub_id   = int(parts[3])

    # Ota subcategoryni topish
    conn = db.get_conn(); c = conn.cursor()
    c.execute("SELECT parent_id FROM subcategories WHERE id=?", (sub_id,))
    row = c.fetchone(); conn.close()

    if row and row["parent_id"]:
        # Ota subcategoryga qaytish
        callback.data = f"cmgr:sub:{cat_slug}:{row['parent_id']}"
        await cb_sub_view(callback, state)
    else:
        # Kategoriyaga qaytish
        callback.data = f"cmgr:view:{cat_slug}"
        await cb_cat_view(callback, state)


# ── Yangi kategoriya (faqat uz nomi) ─────────────────────────────────────────
@router.callback_query(F.data == "cmgr:addcat")
async def cb_addcat(callback: CallbackQuery, state: FSMContext):
    lang = db.get_user_lang(callback.from_user.id)
    await state.set_state(CategoryStates.adding_cat_uz)
    await callback.message.answer(
        "📂 <b>Yangi kategoriya</b>\n\nNomini yozing (o'zbekcha):\n"
        "<i>Misol: Akril, MDF, Laminat</i>",
        parse_mode="HTML",
        reply_markup=cancel_only_keyboard(lang))
    await callback.answer()

@router.message(CategoryStates.adding_cat_uz, F.text)
async def got_cat_name(message: Message, state: FSMContext):
    lang = db.get_user_lang(message.from_user.id)
    uz   = message.text.strip()
    slug = _slug(uz)
    if db.category_exists(slug):
        slug = f"{slug}_{len(db.get_all_categories())}"
    db.add_category(slug, uz, uz, uz)
    await state.set_state(AdminStates.cat_mgr)
    cats = db.get_all_categories()
    await message.answer(f"✅ Kategoriya qo'shildi: <b>{uz}</b>", parse_mode="HTML")
    await message.answer("📂 <b>Kategoriyalar</b>",
                         parse_mode="HTML", reply_markup=_cat_list_kb(lang, cats))


# ── Yangi subkategoriya (istalgan darajada) ───────────────────────────────────
@router.callback_query(F.data.startswith("cmgr:addsub:"))
async def cb_addsub(callback: CallbackQuery, state: FSMContext):
    lang   = db.get_user_lang(callback.from_user.id)
    parts  = callback.data.split(":")
    cat_slug  = parts[2]
    parent_id = int(parts[3])  # 0 = top-level
    await state.update_data(sub_cat=cat_slug, sub_parent=parent_id)
    await state.set_state(CategoryStates.adding_sub_uz)
    # Joylashuvni ko'rsat
    if parent_id:
        conn = db.get_conn(); c = conn.cursor()
        c.execute("SELECT name_uz FROM subcategories WHERE id=?", (parent_id,))
        p = c.fetchone(); conn.close()
        parent_name = p["name_uz"] if p else "?"
        hint = f"📍 Joylashuv: ...→ <b>{parent_name}</b> → yangi"
    else:
        cat = db.get_category(cat_slug)
        hint = f"📍 Joylashuv: <b>{cat[f'name_{lang}']}</b> → yangi"

    await callback.message.answer(
        f"📁 <b>Yangi subkategoriya</b>\n{hint}\n\nNomini yozing:",
        parse_mode="HTML",
        reply_markup=cancel_only_keyboard(lang))
    await callback.answer()

@router.message(CategoryStates.adding_sub_uz, F.text)
async def got_sub_name(message: Message, state: FSMContext):
    lang = db.get_user_lang(message.from_user.id)
    data = await state.get_data()
    cat_slug  = data.get("sub_cat","")
    parent_id = data.get("sub_parent", 0)
    uz   = message.text.strip()
    slug = _slug(uz)

    # Slug unique qilish
    base = slug
    for i in range(1, 100):
        if not db.get_subcategory(cat_slug, slug):
            break
        slug = f"{base}_{i}"

    if parent_id:
        db.add_nested_sub(cat_slug, parent_id, slug, uz)
    else:
        db.add_subcategory(cat_slug, slug, uz, uz, uz)

    await state.set_state(AdminStates.cat_mgr)
    await message.answer(f"✅ Subkategoriya qo'shildi: <b>{uz}</b>", parse_mode="HTML")
    # Kategoriyaga qaytish
    cats = db.get_all_categories()
    await message.answer("📂 <b>Kategoriyalar</b>",
                         parse_mode="HTML", reply_markup=_cat_list_kb(lang, cats))


# ── O'chirish ─────────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("cmgr:delcat:"))
async def cb_delcat(callback: CallbackQuery):
    lang  = db.get_user_lang(callback.from_user.id)
    slug  = callback.data.split(":")[2]
    cat   = db.get_category(slug)
    if not cat: await callback.answer(); return
    cnt   = db.count_products_in_category(slug)
    if cnt > 0:
        await callback.answer(f"⚠️ {cnt} ta mahsulot bor!", show_alert=True); return
    db.delete_category(slug)
    cats = db.get_all_categories()
    await safe_edit_or_send(callback,
        f"🗑 O'chirildi: <b>{cat[f'name_{lang}']}</b>\n\n📂 <b>Kategoriyalar</b>",
        _cat_list_kb(lang, cats))
    await callback.answer()

@router.callback_query(F.data.startswith("cmgr:delsub:"))
async def cb_delsub(callback: CallbackQuery):
    lang     = db.get_user_lang(callback.from_user.id)
    parts    = callback.data.split(":")
    cat_slug = parts[2]; sub_slug = parts[3]
    sub      = db.get_subcategory(cat_slug, sub_slug)
    if not sub: await callback.answer(); return
    cnt = db.count_products_in_subcategory(cat_slug, sub_slug)
    if cnt > 0:
        await callback.answer(f"⚠️ {cnt} ta mahsulot bor!", show_alert=True); return
    db.delete_subcategory(cat_slug, sub_slug)
    await callback.answer("🗑 O'chirildi", show_alert=True)
    # Kategoriyaga qaytish
    callback.data = f"cmgr:view:{cat_slug}"
    await cb_cat_view(callback, None)
