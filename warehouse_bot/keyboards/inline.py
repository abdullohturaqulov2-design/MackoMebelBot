# -*- coding: utf-8 -*-
from typing import List, Optional, Sequence
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import PAGE_SIZE
from locales.texts import t


def paginate(items, page, page_size=PAGE_SIZE):
    total = max(1, (len(items)+page_size-1)//page_size)
    page  = max(0, min(page, total-1))
    s = page*page_size
    return items[s:s+page_size], page, total


def _nav_row(b, lang, page, total, prefix):
    prev = InlineKeyboardButton(text=t(lang,"btn_prev"), callback_data=f"{prefix}:{page-1}") if page>0 else InlineKeyboardButton(text=" ", callback_data="noop")
    mid  = InlineKeyboardButton(text=t(lang,"page_indicator",page=page+1,total=total), callback_data="noop")
    nxt  = InlineKeyboardButton(text=t(lang,"btn_next"), callback_data=f"{prefix}:{page+1}") if page<total-1 else InlineKeyboardButton(text=" ", callback_data="noop")
    b.row(prev, mid, nxt)


def _main_btn(lang):
    return InlineKeyboardButton(text=t(lang,"btn_to_main"), callback_data="to_main")


# ── Ombor: kategoriyalar ──────────────────────────────────────────────────────
def categories_keyboard(lang, cats):
    from database.db import count_products_in_category
    b = InlineKeyboardBuilder()
    for c in cats:
        cnt = count_products_in_category(c["slug"])
        b.button(text=f"{c[f'name_{lang}']} ({cnt})", callback_data=f"catsel:{c['slug']}")
    b.adjust(2)
    b.row(_main_btn(lang))
    return b.as_markup()


def subcategories_keyboard(lang, cat_slug, subs):
    from database.db import count_products_in_subcategory
    b = InlineKeyboardBuilder()
    for s in subs:
        cnt = count_products_in_subcategory(cat_slug, s["slug"])
        b.button(text=f"{s[f'name_{lang}']} ({cnt})", callback_data=f"catsub:{cat_slug}:{s['slug']}")
    b.adjust(1)
    b.row(InlineKeyboardButton(text=t(lang,"btn_back"), callback_data="catshow"),
          _main_btn(lang))
    return b.as_markup()


# ── Mahsulotlar ro'yxati ──────────────────────────────────────────────────────
def products_list_keyboard(lang, page_items, page, total, item_prefix, nav_prefix, back_cb=None):
    b = InlineKeyboardBuilder()
    for p in page_items:
        code  = p["code"] or ""
        label = f"{p['name']} ({code})" if code else p["name"]
        if len(label) > 42: label = label[:39]+"..."
        b.button(text=label, callback_data=f"{item_prefix}:{p['id']}")
    b.adjust(1)
    if total > 1: _nav_row(b, lang, page, total, nav_prefix)
    row = []
    if back_cb: row.append(InlineKeyboardButton(text=t(lang,"btn_back"), callback_data=back_cb))
    row.append(_main_btn(lang))
    b.row(*row)
    return b.as_markup()


def product_detail_back_keyboard(lang, back_cb):
    b = InlineKeyboardBuilder()
    b.button(text=t(lang,"btn_back"), callback_data=back_cb)
    b.button(text=t(lang,"btn_to_main"), callback_data="to_main")
    b.adjust(2)
    return b.as_markup()


def product_detail_admin_keyboard(lang, prod_id, back_cb, has_photo=False, has_qr=False):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    b = InlineKeyboardBuilder()
    b.button(text=t(lang,"btn_mv_in"),   callback_data=f"mvf:IN:{prod_id}")
    b.button(text=t(lang,"btn_mv_out"),  callback_data=f"mvf:OUT:{prod_id}")
    b.button(text=t(lang,"btn_mv_hist"), callback_data=f"mvh:{prod_id}")
    b.button(text=t(lang,"btn_mv_min"),  callback_data=f"mvmq:{prod_id}")
    b.adjust(2)
    if has_photo:
        b.row(InlineKeyboardButton(text=t(lang,"btn_remove_photo"),
                                   callback_data=f"photo:del:{prod_id}"))
    b.row(InlineKeyboardButton(text=t(lang,"btn_upload_photo"),
                               callback_data=f"photo:up:{prod_id}"))
    # QR tugmasi — faqat QR yo'q bo'lsa
    if not has_qr:
        b.row(InlineKeyboardButton(text="📦 QR code berish",
                                   callback_data=f"qr:gen:{prod_id}"))
    b.row(InlineKeyboardButton(text=t(lang,"btn_del_product"),
                               callback_data=f"delprod:ask:{prod_id}"))
    b.row(InlineKeyboardButton(text=t(lang,"btn_back"),  callback_data=back_cb),
          InlineKeyboardButton(text=t(lang,"btn_to_main"), callback_data="to_main"))
    return b.as_markup()


# ── Qo'shilgan / o'chirilgan ──────────────────────────────────────────────────
def added_view_keyboard(lang):
    b = InlineKeyboardBuilder()
    b.button(text=t(lang,"btn_view_added"), callback_data="addlist:0")
    return b.as_markup()


def removed_report_keyboard(lang):
    b = InlineKeyboardBuilder()
    b.button(text=t(lang,"btn_view_removed"),  callback_data="remlist:0")
    b.button(text=t(lang,"btn_view_remaining"), callback_data="keeplist:0")
    b.adjust(1)
    return b.as_markup()


# ── Statistika ────────────────────────────────────────────────────────────────
def stats_keyboard(lang, low_count):
    b = InlineKeyboardBuilder()
    if low_count > 0:
        b.button(text=t(lang,"btn_low_stock",count=low_count), callback_data="lowstock:0")
    b.row(_main_btn(lang))
    return b.as_markup()


def low_stock_keyboard(lang, page, total):
    b = InlineKeyboardBuilder()
    if total > 1: _nav_row(b, lang, page, total, "lowstock")
    b.row(InlineKeyboardButton(text=t(lang,"btn_back"), callback_data="stats_back"),
          _main_btn(lang))
    return b.as_markup()


# ── Kategoriya boshqaruvi ─────────────────────────────────────────────────────
def cat_mgr_list_keyboard(lang, cats):
    b = InlineKeyboardBuilder()
    for c in cats:
        b.button(text=f"📂 {c[f'name_{lang}']}", callback_data=f"cmgr:view:{c['slug']}")
    b.adjust(1)
    b.row(InlineKeyboardButton(text=t(lang,"btn_add_cat"), callback_data="cmgr:addcat"))
    return b.as_markup()


def cat_mgr_detail_keyboard(lang, slug, has_products):
    b = InlineKeyboardBuilder()
    b.button(text=t(lang,"btn_add_sub"), callback_data=f"cmgr:addsub:{slug}")
    if not has_products:
        b.button(text=t(lang,"btn_delete"), callback_data=f"cmgr:delcat:{slug}")
    b.adjust(1)
    b.row(InlineKeyboardButton(text=t(lang,"btn_back"), callback_data="cmgr:list"))
    return b.as_markup()


def sub_mgr_detail_keyboard(lang, cat_slug, subs):
    from database.db import count_products_in_subcategory
    b = InlineKeyboardBuilder()
    for s in subs:
        cnt = count_products_in_subcategory(cat_slug, s["slug"])
        b.button(text=f"🗑 {s[f'name_{lang}']} ({cnt})", callback_data=f"cmgr:delsub:{cat_slug}:{s['slug']}")
    b.adjust(1)
    b.button(text=t(lang,"btn_add_sub"), callback_data=f"cmgr:addsub:{cat_slug}")
    b.button(text=t(lang,"btn_back"), callback_data=f"cmgr:view:{cat_slug}")
    b.adjust(1)
    return b.as_markup()


def confirm_keyboard(lang, yes_cb):
    b = InlineKeyboardBuilder()
    b.button(text=t(lang,"btn_confirm_yes"), callback_data=yes_cb)
    b.button(text=t(lang,"btn_confirm_no"),  callback_data="cmgr:list")
    b.adjust(2)
    return b.as_markup()


# ── Manual qo'shish ───────────────────────────────────────────────────────────
def ma_categories_keyboard(lang, cats):
    """Ombor ko'rish uchun EMAS — manual add uchun. Pastda kategoriya yaratish ham bor."""
    b = InlineKeyboardBuilder()
    for c in cats:
        b.button(text=c[f"name_{lang}"], callback_data=f"macat:{c['slug']}")
    b.adjust(2)
    b.row(InlineKeyboardButton(text=t(lang,"btn_new_cat"), callback_data="ma:newcat"),
          InlineKeyboardButton(text=t(lang,"btn_to_main"), callback_data="to_main"))
    return b.as_markup()


def ma_subcategories_keyboard(lang, cat_slug, subs):
    b = InlineKeyboardBuilder()
    for s in subs:
        b.button(text=s[f"name_{lang}"], callback_data=f"masub:{cat_slug}:{s['slug']}")
    b.adjust(1)
    b.row(InlineKeyboardButton(text=t(lang,"btn_skip"),    callback_data="masub:skip:skip"),
          InlineKeyboardButton(text=t(lang,"btn_new_sub"), callback_data=f"ma:newsub:{cat_slug}"))
    b.row(InlineKeyboardButton(text=t(lang,"btn_back"),    callback_data="masub:back"),
          InlineKeyboardButton(text=t(lang,"btn_to_main"), callback_data="to_main"))
    return b.as_markup()


def skip_keyboard(lang):
    b = InlineKeyboardBuilder()
    b.button(text=t(lang,"btn_skip"), callback_data="ma:skip")
    b.button(text=t(lang,"btn_to_main"), callback_data="to_main")
    b.adjust(2)
    return b.as_markup()


def skip_photo_keyboard(lang):
    b = InlineKeyboardBuilder()
    b.button(text=t(lang,"btn_skip"), callback_data="ma:skip_photo")
    b.button(text=t(lang,"btn_to_main"), callback_data="to_main")
    b.adjust(2)
    return b.as_markup()


def ma_confirm_keyboard(lang):
    b = InlineKeyboardBuilder()
    b.button(text=t(lang,"btn_confirm_add"), callback_data="ma:confirm")
    b.button(text=t(lang,"btn_edit"),        callback_data="ma:edit")
    b.button(text=t(lang,"btn_cancel_add"),  callback_data="ma:cancel")
    b.adjust(2)
    return b.as_markup()


def ma_edit_fields_keyboard(lang):
    """Qaysi maydonni tahrirlash kerakligini tanlash."""
    fields = [
        ("📦 Nomi",          "maedit:name"),
        ("🔢 Kodi",          "maedit:code"),
        ("📂 Kategoriya",    "maedit:category"),
        ("📁 Subkategoriya", "maedit:subcategory"),
        ("📐 Format",        "maedit:format"),
        ("📏 Qalinlik",      "maedit:thickness"),
        ("💰 Narx",          "maedit:price"),
        ("📊 Miqdor",        "maedit:quantity"),
        ("📍 Joylashuv",     "maedit:location"),
    ]
    b = InlineKeyboardBuilder()
    for label, cb in fields:
        b.button(text=label, callback_data=cb)
    b.adjust(2)
    b.row(InlineKeyboardButton(text=t(lang,"btn_edit_done"), callback_data="maedit:done"))
    return b.as_markup()


# ── Excel tasdiqlash ──────────────────────────────────────────────────────────
def excel_confirm_keyboard(lang):
    b = InlineKeyboardBuilder()
    b.button(text=t(lang,"btn_confirm_add"), callback_data="excadd:confirm")
    b.button(text=t(lang,"btn_edit"),        callback_data="excadd:edit")
    b.button(text=t(lang,"btn_cancel_add"),  callback_data="excadd:cancel")
    b.adjust(2)
    return b.as_markup()


def excel_del_confirm_keyboard(lang):
    b = InlineKeyboardBuilder()
    b.button(text=t(lang,"btn_confirm_yes"), callback_data="excdel:confirm")
    b.button(text=t(lang,"btn_edit"),        callback_data="excdel:edit")
    b.button(text=t(lang,"btn_confirm_no"),  callback_data="excdel:cancel")
    b.adjust(2)
    return b.as_markup()


# ── Manual o'chirish ──────────────────────────────────────────────────────────
def md_confirm_keyboard(lang, prod_id):
    b = InlineKeyboardBuilder()
    b.button(text=t(lang,"btn_confirm_yes"), callback_data=f"md:confirm:{prod_id}")
    b.button(text=t(lang,"btn_confirm_no"),  callback_data="md:cancel")
    b.adjust(2)
    return b.as_markup()


def md_search_keyboard(lang, rows):
    b = InlineKeyboardBuilder()
    for p in rows[:10]:
        code  = p["code"] or "-"
        label = f"{p['name']} ({code})"
        if len(label) > 40: label = label[:37]+"..."
        b.button(text=label, callback_data=f"md:sel:{p['id']}")
    b.adjust(1)
    b.row(InlineKeyboardButton(text=t(lang,"btn_cancel_add"), callback_data="md:cancel"))
    return b.as_markup()


# ── Tarix ─────────────────────────────────────────────────────────────────────
def history_days_keyboard(lang, days, page, total_pages):
    b = InlineKeyboardBuilder()
    for d in days:
        label = t(lang,"hist_day_btn", date=d["day"], total=int(d["total"]))
        b.button(text=f"📅 {label}", callback_data=f"hist:day:{d['day']}")
    b.adjust(2)
    if total_pages > 1: _nav_row(b, lang, page, total_pages, "hist:pg")
    b.row(_main_btn(lang))
    return b.as_markup()


def history_day_back_keyboard(lang, page):
    b = InlineKeyboardBuilder()
    b.button(text=t(lang,"btn_back"),    callback_data=f"hist:pg:{page}")
    b.button(text=t(lang,"btn_to_main"), callback_data="to_main")
    b.adjust(2)
    return b.as_markup()


# ── Admin boshqaruvi ──────────────────────────────────────────────────────────
def admin_mgr_keyboard(lang, admins, superadmin_ids):
    b = InlineKeyboardBuilder()
    for a in admins:
        uid  = a["user_id"]
        name = a["full_name"] or a["username"] or str(uid)
        can_remove = uid not in superadmin_ids
        b.button(text=f"{'🔴' if can_remove else '🔒'} {name}",
                 callback_data=f"admgr:del:{uid}" if can_remove else "noop")
    b.adjust(1)
    b.row(InlineKeyboardButton(text=t(lang,"btn_add_admin"), callback_data="admgr:add"))
    return b.as_markup()


def admin_confirm_keyboard(lang, uid):
    b = InlineKeyboardBuilder()
    b.button(text=t(lang,"btn_confirm_yes"), callback_data=f"admgr:confirm:{uid}")
    b.button(text=t(lang,"btn_confirm_no"),  callback_data="admgr:list")
    b.adjust(2)
    return b.as_markup()


# ── Kirim/Chiqim ────────────────────────────────────────────────────────────
def mv_type_keyboard(lang):
    b = InlineKeyboardBuilder()
    b.button(text=t(lang,"mv_btn_in"),  callback_data="mv:IN")
    b.button(text=t(lang,"mv_btn_out"), callback_data="mv:OUT")
    b.adjust(2)
    return b.as_markup()

def mv_note_keyboard(lang):
    b = InlineKeyboardBuilder()
    b.button(text=t(lang,"mv_btn_skip"), callback_data="mv:skip_note")
    return b.as_markup()


def del_prod_confirm_keyboard(lang, prod_id):
    b = InlineKeyboardBuilder()
    b.button(text=t(lang,"btn_confirm_yes"), callback_data=f"delprod:confirm:{prod_id}")
    b.button(text=t(lang,"btn_confirm_no"),  callback_data=f"delprod:cancel:{prod_id}")
    b.adjust(2)
    return b.as_markup()
