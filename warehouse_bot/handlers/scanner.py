# -*- coding: utf-8 -*-
"""
QR Scanner handler.
1. Foydalanuvchi "🔍 Skaner" bosganda → Mini App ochadi
2. Mini App QR ni skaner qilib → bot ga data yuboradi
3. Bot bazadan mahsulot topadi → maʼlumot chiqaradi
"""
import json
import logging
import os

from aiogram import Router, F
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

from database import db
from locales.texts import TEXTS, t
from utils.render import send_product_detail
from utils.access import is_admin

router = Router()
logger = logging.getLogger(__name__)


def get_scanner_webapp_url() -> str:
    """GitHub Pages yoki boshqa hosting URL."""
    url = os.environ.get("WEBAPP_SCANNER_URL", "").strip()
    return url


def scanner_keyboard(lang: str) -> ReplyKeyboardMarkup:
    """Skaner boshlash inline-button."""
    url = get_scanner_webapp_url()
    if not url:
        return None
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(
            text="📷 Skaner boshlash",
            web_app=WebAppInfo(url=url)
        )]],
        resize_keyboard=True,
        one_time_keyboard=True
    )


# ── Foydalanuvchi "Skaner" reply button bosadi ────────────────────────────────
def _all(k): return {TEXTS[l].get(k,"") for l in TEXTS} - {""}



@router.message(F.text.in_(_all("btn_scanner")))
async def open_scanner(message: Message, state: FSMContext):
    uid  = message.from_user.id
    lang = db.get_user_lang(uid)
    url  = get_scanner_webapp_url()

    if not url:
        await message.answer("⚠️ Skaner sozlanmagan.")
        return

    # Skaner + Asosiy sahifa tugmasi
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(
                text="📷 Skaner boshlash",
                web_app=WebAppInfo(url=url)
            )],
            [KeyboardButton(text=t(lang, "btn_back_main"))],  # ← YANGI
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(
        "📷 <b>QR Skaner</b>\n\n"
        "Skanerlamoqchi bo'lsangiz pastdagi tugmani bosing.\n"
        "Kamera ochiladi → QR codeni ramkaga to'g'irlang.",
        parse_mode="HTML",
        reply_markup=kb
    )


# ── Mini App dan QR data keladi ───────────────────────────────────────────────
@router.message(F.web_app_data)
async def handle_qr_data(message: Message):
    uid  = message.from_user.id
    lang = db.get_user_lang(uid)
    raw  = message.web_app_data.data

    # JSON parse
    try:
        data = json.loads(raw)
        qr_code = data.get("qr", "").strip()
    except (json.JSONDecodeError, AttributeError):
        qr_code = raw.strip()

    if not qr_code:
        await message.answer("⚠️ Skanerlash noto'g'ri ketdi. Qaytadan urinib ko'ring.")
        return

    # Bazadan qidirish — kod bo'yicha
    products = db.search_by_code(qr_code)

    # ID bo'yicha ham qidirish (#123 format)
    if not products and qr_code.startswith("#"):
        try:
            pid  = int(qr_code[1:])
            prod = db.get_product(pid)
            if prod: products = [prod]
        except ValueError:
            pass

    # Nom bo'yicha ham qidirish (fallback)
    if not products:
        products = db.search_by_name(qr_code)

    if not products:
        await message.answer(
            f"❌ QR kodga mos mahsulot topilmadi.\n"
            f"<code>{qr_code}</code>\n\n"
            "Qaytadan urinib ko'ring.",
            parse_mode="HTML"
        )
        return

    # Topildi → birinchi natijani ko'rsat
    prod  = products[0]
    admin = is_admin(uid)
    await message.answer(f"✅ Muvaffaqiyatli skanerlash! ({qr_code})")
    await send_product_detail(message, lang, prod, "catshow", admin=admin)

    # Bir nechta topilsa — qolganlari ham
    if len(products) > 1:
        from keyboards.inline import products_list_keyboard
        from utils.cache import SEARCH_CACHE
        SEARCH_CACHE[uid] = {"field":"code","value":qr_code}
        from utils.render import send_products_list
        await send_products_list(
            message, lang, products[1:], 0,
            "srchprod:0", "srchlist", "search_results_title"
        )
