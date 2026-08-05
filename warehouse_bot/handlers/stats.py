from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from database import db
from locales.texts import TEXTS, t
from keyboards.inline import stats_keyboard, low_stock_keyboard, products_list_keyboard, product_detail_back_keyboard, paginate
from utils.access import is_admin
from utils.render import delete_msg
from utils.render import send_product_detail

router = Router()

def _all(key): return {TEXTS[l][key] for l in TEXTS}

@router.message(F.text.in_(_all("btn_stats")))
async def show_stats(message: Message):
    if not is_admin(message.from_user.id): return
    await delete_msg(message)
    lang  = db.get_user_lang(message.from_user.id)
    s     = db.get_stats()
    await message.answer(t(lang,"stats_title",**s), parse_mode="HTML",
                         reply_markup=stats_keyboard(lang, s["low_stock_count"]))

@router.callback_query(F.data == "stats_back")
async def cb_stats_back(callback: CallbackQuery):
    lang = db.get_user_lang(callback.from_user.id)
    s    = db.get_stats()
    try:
        await callback.message.edit_text(t(lang,"stats_title",**s), parse_mode="HTML",
                                         reply_markup=stats_keyboard(lang, s["low_stock_count"]))
    except: pass
    await callback.answer()

@router.callback_query(F.data.startswith("lowstock:"))
async def cb_lowstock(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer(); return
    lang  = db.get_user_lang(callback.from_user.id)
    page  = int(callback.data.split(":")[1])
    rows  = db.get_low_stock_products()
    if not rows:
        await callback.answer(t(lang,"no_low_stock"), show_alert=True); return
    items, page, total = paginate(rows, page)
    kb = products_list_keyboard(lang, items, page, total,
                                f"lsprod:{page}", "lowstock",
                                back_cb="stats_back")
    try:    await callback.message.edit_text(t(lang,"low_stock_title"), parse_mode="HTML", reply_markup=kb)
    except: await callback.message.answer(t(lang,"low_stock_title"), parse_mode="HTML", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("lsprod:"))
async def cb_lsprod(callback: CallbackQuery):
    lang = db.get_user_lang(callback.from_user.id)
    _, page_str, pid = callback.data.split(":", 2)
    prod = db.get_product(int(pid))
    if not prod: await callback.answer(); return
    await send_product_detail(callback, lang, prod, f"lowstock:{page_str}", admin=True)
    await callback.answer()
