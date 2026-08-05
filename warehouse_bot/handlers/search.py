# -*- coding: utf-8 -*-
import re, os, uuid, logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import db
from locales.texts import t
from config import DATA_DIR
from keyboards.inline import categories_keyboard, subcategories_keyboard
from utils.render import send_products_list, send_product_detail
from utils.cache import SEARCH_CACHE
from utils.access import is_admin
from states.states import AdminStates

router  = Router()
logger  = logging.getLogger(__name__)
TMP_DIR = os.path.join(DATA_DIR, "tmp")

KROMKA_RE = re.compile(r"^\s*(\d+)\s*/\s*(\d+[.,]?\d*)\s*$")
SIZE_RE   = re.compile(r"^\s*(\d{3,4})\s*[xXхХ*]\s*(\d{3,4})\s*$")
THICK_RE  = re.compile(r"^\s*(\d+([.,]\d+)?)\s*(sm|mm|мм|см)?\s*$", re.IGNORECASE)


def _cache_rows(c):
    f, v = c.get("field"), c.get("value", "")
    if f == "image_analysis":
        from utils.vision_search import search_by_analysis
        return search_by_analysis(v)
    if f == "kromka_format": return db.search_kromka_by_format(v)
    if f == "format":        return db.search_by_format(v)
    if f == "thickness":     return db.search_by_thickness(v)
    if f == "code":          return db.search_by_code(v)
    return db.search_by_name(v)


# ── Matn orqali qidiruv ───────────────────────────────────────────────────────
@router.message(AdminStates.main_menu, F.text)
async def free_search(message: Message):
    lang  = db.get_user_lang(message.from_user.id)
    text  = message.text.strip()
    lower = text.lower()
    uid   = message.from_user.id

    cat = db.get_category(lower)
    if cat:
        subs = db.get_subcategories(lower)
        if subs:
            await message.answer(t(lang,"choose_subcategory"),
                                 reply_markup=subcategories_keyboard(lang, lower, subs))
        else:
            rows = db.get_products_by_category(lower)
            await send_products_list(message, lang, rows, 0,
                f"catprod:{lower}:_:0", f"catlist:{lower}:_",
                "product_list_title", "catshow")
        return

    rows, field, value = [], None, text

    m = KROMKA_RE.match(text)
    if m:
        value=f"{m.group(1)}/{m.group(2)}"; rows=db.search_kromka_by_format(value); field="kromka_format"
    if not rows:
        m = SIZE_RE.match(text)
        if m: value=f"{m.group(1)}*{m.group(2)}"; rows=db.search_by_format(value); field="format"
    if not rows:
        m = THICK_RE.match(text)
        if m: value=m.group(1).replace(",","."); rows=db.search_by_thickness(value); field="thickness"
    if not rows:
        r = db.search_by_code(text)
        if r: rows, field, value = r, "code", text
    if not rows:
        r = db.search_by_name(text)
        if r: rows, field, value = r, "name", text

    if not rows:
        await message.answer(t(lang, "product_not_found")); return

    SEARCH_CACHE[uid] = {"field": field, "value": value}
    await send_products_list(message, lang, rows, 0,
        "srchprod:0", "srchlist", "search_results_title")


@router.callback_query(F.data.startswith("srchlist:"))
async def cb_srchlist(callback: CallbackQuery):
    lang = db.get_user_lang(callback.from_user.id)
    page = int(callback.data.split(":")[1])
    rows = _cache_rows(SEARCH_CACHE.get(callback.from_user.id, {}))
    await send_products_list(callback, lang, rows, page,
        f"srchprod:{page}", "srchlist", "search_results_title", edit=True)
    await callback.answer()


@router.callback_query(F.data.startswith("srchprod:"))
async def cb_srchprod(callback: CallbackQuery):
    lang = db.get_user_lang(callback.from_user.id)
    _, pg, pid = callback.data.split(":", 2)
    prod = db.get_product(int(pid))
    if not prod:
        await callback.answer(t(lang, "product_not_found"), show_alert=True); return
    await send_product_detail(callback, lang, prod, f"srchlist:{pg}",
                              admin=is_admin(callback.from_user.id))
    await callback.answer()


# ── Rasm orqali qidiruv (FALLBACK — oxirgi ushlaydi) ─────────────────────────
@router.message(F.photo)
async def handle_photo_search(message: Message, state: FSMContext, bot: Bot):
    """
    Barcha rasm xabarlarini ushlaydi (boshqa handler ushlamagan bo'lsa).
    Bu handler search.router da — oxirgi router, shuning uchun
    PhotoStates, ManualAddStates kabi maxsus holatlardagi handlerlar
    avval ishlaydi, qolgani bu yerga tushadi.
    """
    uid           = message.from_user.id
    current_state = await state.get_state()

    # Maxsus holatlarda boshqa handlerlar ishlaydi —
    # lekin agar bu yerga yetib kelsa, rasm qidiruvga tushamiz
    lang = db.get_user_lang(uid)

    # Foydalanuvchi birinchi marta — til tanlash
    if not db.user_has_language(uid):
        from keyboards.reply import language_keyboard
        await state.set_state(AdminStates.choosing_language)
        await message.answer(t("uz","choose_language"), reply_markup=language_keyboard())
        return

    # Holat yo'q bo'lsa — main_menu ga o'rnat
    if current_state is None:
        await state.set_state(AdminStates.main_menu)

    # GEMINI_API_KEY ni har safar environment dan o'qish
    import os as _os
    _api_key = (
        _os.environ.get("GEMINI_API_KEY") or
        _os.environ.get("GOOGLE_API_KEY") or
        _os.environ.get("GOOGLE_GEMINI_KEY") or ""
    )
    if not _api_key:
        try:
            from dotenv import load_dotenv as _ld
            _ld(override=True)
            _api_key = (
                _os.environ.get("GEMINI_API_KEY") or
                _os.environ.get("GOOGLE_API_KEY") or ""
            )
        except Exception:
            pass
    if not _api_key:
        await message.answer(t(lang, "img_no_api"))
        return


    proc_msg = await message.answer(t(lang, "img_processing"))

    # Rasmni yuklab olish
    photo     = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    os.makedirs(TMP_DIR, exist_ok=True)
    img_path  = os.path.join(TMP_DIR, f"srch_{uid}_{uuid.uuid4().hex[:8]}.jpg")

    try:
        await bot.download_file(file_info.file_path, destination=img_path)
    except Exception as e:
        try: await proc_msg.delete()
        except: pass
        await message.answer(t(lang, "img_error"))
        logger.error(f"Rasm yuklab olish xatosi: {e}")
        return

    # Gemini AI tahlil
    try:
        from utils.vision_search import analyze_image, search_by_analysis, build_detected_info
        analysis = analyze_image(img_path)
    except Exception as e:
        try: await proc_msg.delete()
        except: pass
        await message.answer(t(lang, "img_error"))
        logger.error(f"vision_search xatosi: {e}")
        try: os.remove(img_path)
        except: pass
        return

    try: os.remove(img_path)
    except: pass
    try: await proc_msg.delete()
    except: pass

    if "error" in analysis:
        err = analysis["error"]
        await message.answer(t(lang,"img_no_api") if err=="no_api_key" else t(lang,"img_error"))
        return

    rows = search_by_analysis(analysis)
    desc = analysis.get("description","") or build_detected_info(analysis)
    SEARCH_CACHE[uid] = {"field":"image_analysis","value":analysis}

    if not rows:
        await message.answer(t(lang,"img_not_found",description=desc), parse_mode="HTML")
        return

    await message.answer(t(lang,"img_found",description=desc), parse_mode="HTML")
    await send_products_list(message, lang, rows, 0,
        "imgsrch:0", "imglist", "search_results_title")


# imglist va imgsrch callbacklari
@router.callback_query(F.data.startswith("imglist:"))
async def cb_imglist(callback: CallbackQuery):
    lang     = db.get_user_lang(callback.from_user.id)
    page     = int(callback.data.split(":")[1])
    cache    = SEARCH_CACHE.get(callback.from_user.id, {})
    analysis = cache.get("value") if cache.get("field")=="image_analysis" else {}
    if not analysis:
        await callback.answer(t(lang,"product_not_found"), show_alert=True); return
    from utils.vision_search import search_by_analysis
    rows = search_by_analysis(analysis)
    await send_products_list(callback, lang, rows, page,
        f"imgsrch:{page}", "imglist", "search_results_title", edit=True)
    await callback.answer()


@router.callback_query(F.data.startswith("imgsrch:"))
async def cb_imgsrch(callback: CallbackQuery):
    lang = db.get_user_lang(callback.from_user.id)
    _, pg, pid = callback.data.split(":", 2)
    prod = db.get_product(int(pid))
    if not prod:
        await callback.answer(t(lang,"product_not_found"), show_alert=True); return
    await send_product_detail(callback, lang, prod, f"imglist:{pg}",
                              admin=is_admin(callback.from_user.id))
    await callback.answer()
