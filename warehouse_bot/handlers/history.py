# -*- coding: utf-8 -*-
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from database import db
from locales.texts import TEXTS, t
from keyboards.inline import history_days_keyboard, history_day_back_keyboard, paginate
from utils.access import is_admin
from utils.render import delete_msg

router = Router()

DAYS_PER_PAGE = 10


def _all(key):
    return {TEXTS[l][key] for l in TEXTS}


def _format_day_report(lang: str, date_str: str) -> str:
    """Bir kun uchun to'liq hisobot matni."""
    products, movements = db.get_day_detail(date_str)
    s = db.get_day_summary(date_str)

    # Sana sarlavhasi
    text = t(lang, "hist_day_title", date=date_str)

    # ── Qo'shilgan mahsulotlar ───────────────────────────────────────────────
    text += t(lang, "hist_added_sec", count=len(products))
    if products:
        for p in products:
            code = p["code"] or "-"
            time = p["added_at"][11:16]          # HH:MM
            name = p["name"]
            if len(name) > 28:
                name = name[:25] + "..."
            text += t(lang, "hist_added_item",
                      name=name, code=code, time=time)
    else:
        text += t(lang, "hist_no_added")

    # ── Harakatlar ───────────────────────────────────────────────────────────
    text += t(lang, "hist_mv_sec")
    if movements:
        for m in movements:
            emoji    = "📥" if m["movement_type"] == "IN" else "📤"
            prod_name= (m["prod_name"] or "?")
            if len(prod_name) > 20:
                prod_name = prod_name[:17] + "..."
            admin_name = (m["admin_name"] or str(m["admin_id"]))
            if len(admin_name) > 12:
                admin_name = admin_name[:10] + "…"
            time = m["created_at"][11:16]
            text += t(lang, "hist_mv_item",
                      emoji=emoji,
                      qty=int(m["quantity"]) if m["quantity"] == int(m["quantity"]) else m["quantity"],
                      prod=prod_name,
                      admin=admin_name,
                      time=time)
    else:
        text += t(lang, "hist_no_mv")

    # ── Jami ─────────────────────────────────────────────────────────────────
    if s["in_cnt"] > 0 or s["out_cnt"] > 0:
        text += t(lang, "hist_summary",
                  in_total =int(s["in_total"]),
                  in_cnt   =s["in_cnt"],
                  out_total=int(s["out_total"]),
                  out_cnt  =s["out_cnt"])

    return text


def _days_page(lang, page):
    """Kunlar sahifasini ko'rsatish uchun matn + keyboard qaytaradi."""
    all_days = db.get_active_days(limit=90)
    if not all_days:
        return t(lang, "history_empty"), None

    items, page, total = paginate(all_days, page, page_size=DAYS_PER_PAGE)
    kb = history_days_keyboard(lang, items, page, total)
    text = t(lang, "history_title")
    return text, kb


# ── Reply tugma: "📅 Tarix" ───────────────────────────────────────────────────
@router.message(F.text.in_(_all("btn_history")))
async def show_history(message: Message):
    if not is_admin(message.from_user.id):
        return
    await delete_msg(message)
    lang = db.get_user_lang(message.from_user.id)
    text, kb = _days_page(lang, 0)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


# ── Sahifalash: "hist:pg:{page}" ─────────────────────────────────────────────
@router.callback_query(F.data.startswith("hist:pg:"))
async def cb_hist_page(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return
    lang = db.get_user_lang(callback.from_user.id)
    page = int(callback.data.split(":")[2])
    text, kb = _days_page(lang, page)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


# ── Kun tanlash: "hist:day:{date}" ───────────────────────────────────────────
@router.callback_query(F.data.startswith("hist:day:"))
async def cb_hist_day(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return
    lang      = db.get_user_lang(callback.from_user.id)
    date_str  = callback.data.split(":", 2)[2]          # YYYY-MM-DD
    report    = _format_day_report(lang, date_str)

    # Qaysi sahifada edi — ortga bosilganda o'sha sahifaga qaytsin
    all_days  = db.get_active_days(limit=90)
    day_slugs = [d["day"] for d in all_days]
    try:
        idx  = day_slugs.index(date_str)
        page = idx // DAYS_PER_PAGE
    except ValueError:
        page = 0

    kb = history_day_back_keyboard(lang, page)

    # Matn juda uzun bo'lsa kesib yuboramiz (Telegram limiti 4096 belgi)
    if len(report) > 4000:
        report = report[:3950] + "\n\n⚠️ Matn qisqartirildi (juda uzun)."

    try:
        await callback.message.edit_text(report, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await callback.message.answer(report, reply_markup=kb, parse_mode="HTML")
    await callback.answer()
