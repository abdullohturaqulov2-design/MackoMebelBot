from aiogram import Router, F
from aiogram.types import CallbackQuery
from database import db
from locales.texts import t
from utils.render import send_products_list, send_product_detail
from utils.cache import ADDED_CACHE, REMOVED_CACHE, REMAINING_CACHE
from utils.access import is_admin

router = Router()

@router.callback_query(F.data.startswith("addlist:"))
async def cb_addlist(callback: CallbackQuery):
    lang=db.get_user_lang(callback.from_user.id); page=int(callback.data.split(":")[1])
    rows=db.get_products_by_ids(ADDED_CACHE.get(callback.from_user.id,[]))
    await send_products_list(callback,lang,rows,page,f"addprod:{page}","addlist","product_list_title",edit=True)
    await callback.answer()

@router.callback_query(F.data.startswith("addprod:"))
async def cb_addprod(callback: CallbackQuery):
    lang=db.get_user_lang(callback.from_user.id); _,pg,pid=callback.data.split(":",2)
    prod=db.get_product(int(pid))
    if not prod: await callback.answer(t(lang,"product_not_found"),show_alert=True); return
    await send_product_detail(callback,lang,prod,f"addlist:{pg}", admin=is_admin(callback.from_user.id))
    await callback.answer()

@router.callback_query(F.data.startswith("remlist:"))
async def cb_remlist(callback: CallbackQuery):
    lang=db.get_user_lang(callback.from_user.id); page=int(callback.data.split(":")[1])
    rows=REMOVED_CACHE.get(callback.from_user.id,[])
    await send_products_list(callback,lang,rows,page,f"remprod:{page}","remlist","product_list_title",edit=True)
    await callback.answer()

@router.callback_query(F.data.startswith("remprod:"))
async def cb_remprod(callback: CallbackQuery):
    lang=db.get_user_lang(callback.from_user.id); _,pg,pid=callback.data.split(":",2)
    rows=REMOVED_CACHE.get(callback.from_user.id,[])
    prod=next((r for r in rows if str(r.get("id",""))==pid),None)
    if not prod: await callback.answer(t(lang,"product_not_found"),show_alert=True); return
    await send_product_detail(callback,lang,prod,f"remlist:{pg}")
    await callback.answer()

@router.callback_query(F.data.startswith("keeplist:"))
async def cb_keeplist(callback: CallbackQuery):
    lang=db.get_user_lang(callback.from_user.id); page=int(callback.data.split(":")[1])
    rows=db.get_products_by_ids(REMAINING_CACHE.get(callback.from_user.id,[]))
    await send_products_list(callback,lang,rows,page,f"keepprod:{page}","keeplist","product_list_title",edit=True)
    await callback.answer()

@router.callback_query(F.data.startswith("keepprod:"))
async def cb_keepprod(callback: CallbackQuery):
    lang=db.get_user_lang(callback.from_user.id); _,pg,pid=callback.data.split(":",2)
    prod=db.get_product(int(pid))
    if not prod: await callback.answer(t(lang,"product_not_found"),show_alert=True); return
    await send_product_detail(callback,lang,prod,f"keeplist:{pg}", admin=is_admin(callback.from_user.id))
    await callback.answer()
