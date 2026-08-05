# -*- coding: utf-8 -*-
import os, uuid, logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import db
from config import GEMINI_API_KEY, DATA_DIR
from locales.texts import t
from utils.render import send_products_list, send_product_detail
from utils.cache import SEARCH_CACHE
from utils.access import is_admin
from states.states import AdminStates, PhotoStates, ManualAddStates

router  = Router()
logger  = logging.getLogger(__name__)
TMP_DIR = os.path.join(DATA_DIR, "tmp")

BUSY_STATES = {
    PhotoStates.waiting_photo.state,
    ManualAddStates.waiting_image.state,
}


@router.message(F.photo)
async def handle_image_search(message: Message, state: FSMContext, bot: Bot):
    uid           = message.from_user.id
    current_state = await state.get_state()

    if current_state in BUSY_STATES:
        return

    lang = db.get_user_lang(uid)

    if not db.user_has_language(uid):
        from keyboards.reply import language_keyboard
        await state.set_state(AdminStates.choosing_language)
        await message.answer(t("uz", "choose_language"), reply_markup=language_keyboard())
        return

    if current_state is None:
        await state.set_state(AdminStates.main_menu)

    if not GEMINI_API_KEY:
        await message.answer(t(lang, "img_no_api"))
        return

    proc_msg = await message.answer(t(lang, "img_processing"))

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

    from utils.vision_search import analyze_image, search_by_analysis, build_detected_info
    
    # Gemini AI tahlil
    analysis = analyze_image(img_path)

    # Tahlildan keyin faylni xavfsiz o'chirish
    if os.path.exists(img_path):
        try: os.remove(img_path)
        except: pass

    try: await proc_msg.delete()
    except: pass

    # Agar tahlilda xatolik bo'lsa
    if "error" in analysis:
        err = analysis["error"]
        logger.error(f"AI Vision Search xatosi: {err}")
        if err == "no_api_key":
            await message.answer(t(lang, "img_no_api"))
        else:
            # Aniq xatoni ekranga chiqarish (diagnostika uchun)
            await message.answer(f"⚠️ Rasm tahlilida xato yuz berdi:\n`{err}`")
        return

    rows     = search_by_analysis(analysis)
    desc     = analysis.get("description", "") or build_detected_info(analysis)
    SEARCH_CACHE[uid] = {"field": "image_analysis", "value": analysis}

    if not rows:
        await message.answer(t(lang, "img_not_found", description=desc), parse_mode="HTML")
        return

    await message.answer(t(lang, "img_found", description=desc), parse_mode="HTML")
    await send_products_list(
        message, lang, rows, 0,
        item_prefix="imgsrch:0",
        nav_prefix="imglist",
        title_key="search_results_title",
    )


@router.callback_query(F.data.startswith("imglist:"))
async def cb_imglist(callback: CallbackQuery):
    lang     = db.get_user_lang(callback.from_user.id)
    page     = int(callback.data.split(":")[1])
    cache    = SEARCH_CACHE.get(callback.from_user.id, {})
    analysis = cache.get("value") if cache.get("field") == "image_analysis" else {}
    if not analysis:
        await callback.answer(t(lang, "product_not_found"), show_alert=True); return
    from utils.vision_search import search_by_analysis
    rows = search_by_analysis(analysis)
    await send_products_list(callback, lang, rows, page,
        item_prefix=f"imgsrch:{page}", nav_prefix="imglist",
        title_key="search_results_title", edit=True)
    await callback.answer()


@router.callback_query(F.data.startswith("imgsrch:"))
async def cb_imgsrch(callback: CallbackQuery):
    lang = db.get_user_lang(callback.from_user.id)
    _, page_str, pid = callback.data.split(":", 2)
    prod = db.get_product(int(pid))
    if not prod:
        await callback.answer(t(lang, "product_not_found"), show_alert=True); return
    await send_product_detail(callback, lang, prod,
                              f"imglist:{page_str}",
                              admin=is_admin(callback.from_user.id))
    await callback.answer()