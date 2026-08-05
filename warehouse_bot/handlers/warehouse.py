from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from database import db
from locales.texts import TEXTS as AT, t
from keyboards.inline import categories_keyboard, subcategories_keyboard, product_detail_back_keyboard
from utils.render import send_products_list, send_product_detail, safe_edit_or_send, delete_msg
from utils.access import is_admin
from states.states import AdminStates

router = Router()
def _wh(k): return {AT[l][k] for l in AT}

@router.message(AdminStates.main_menu, F.text.in_(_wh("btn_warehouse")))
async def open_wh(message: Message):
    await delete_msg(message)
    lang = db.get_user_lang(message.from_user.id)
    cats = db.get_all_categories()
    await message.answer(t(lang,"choose_category"), reply_markup=categories_keyboard(lang,cats))

@router.callback_query(F.data == "catshow")
async def cb_catshow(callback: CallbackQuery):
    lang = db.get_user_lang(callback.from_user.id)
    cats = db.get_all_categories()
    await safe_edit_or_send(callback, t(lang,"choose_category"), categories_keyboard(lang,cats))
    await callback.answer()

@router.callback_query(F.data.startswith("catsel:"))
async def cb_catsel(callback: CallbackQuery):
    lang = db.get_user_lang(callback.from_user.id)
    cat  = callback.data.split(":",1)[1]
    subs = db.get_subcategories(cat)
    if subs:
        await safe_edit_or_send(callback, t(lang,"choose_subcategory"), subcategories_keyboard(lang,cat,subs))
    else:
        rows = db.get_products_by_category(cat)
        await send_products_list(callback,lang,rows,0,
            item_prefix=f"catprod:{cat}:_:0", nav_prefix=f"catlist:{cat}:_",
            title_key="product_list_title", back_cb="catshow", edit=True)
    await callback.answer()

@router.callback_query(F.data.startswith("catsub:"))
async def cb_catsub(callback: CallbackQuery):
    lang = db.get_user_lang(callback.from_user.id)
    _,cat,sub = callback.data.split(":",2)
    rows = db.get_products_by_category(cat,sub)
    await send_products_list(callback,lang,rows,0,
        item_prefix=f"catprod:{cat}:{sub}:0", nav_prefix=f"catlist:{cat}:{sub}",
        title_key="product_list_title", back_cb=f"catsel:{cat}", edit=True)
    await callback.answer()

@router.callback_query(F.data.startswith("catlist:"))
async def cb_catlist(callback: CallbackQuery):
    lang = db.get_user_lang(callback.from_user.id)
    _,cat,sub,pg = callback.data.split(":",3)
    page = int(pg)
    rows = db.get_products_by_category(cat, None if sub=="_" else sub)
    back = f"catsel:{cat}" if sub!="_" else "catshow"
    await send_products_list(callback,lang,rows,page,
        item_prefix=f"catprod:{cat}:{sub}:{page}", nav_prefix=f"catlist:{cat}:{sub}",
        title_key="product_list_title", back_cb=back, edit=True)
    await callback.answer()

@router.callback_query(F.data.startswith("catprod:"))
async def cb_catprod(callback: CallbackQuery):
    lang  = db.get_user_lang(callback.from_user.id)
    _,cat,sub,pg,pid = callback.data.split(":",4)
    prod  = db.get_product(int(pid))
    if not prod: await callback.answer(t(lang,"product_not_found"),show_alert=True); return
    admin = is_admin(callback.from_user.id)
    await send_product_detail(callback,lang,prod,f"catlist:{cat}:{sub}:{pg}", admin=admin)
    await callback.answer()

@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery): await callback.answer()


@router.callback_query(F.data == "to_main")
async def cb_to_main(callback: CallbackQuery, state: FSMContext):
    from keyboards.reply import get_main_keyboard
    from utils.access import get_role_level
    from utils.render import delete_msg
    lang = db.get_user_lang(callback.from_user.id)
    role = get_role_level(callback.from_user.id)
    await delete_msg(callback.message)
    await state.set_state(AdminStates.main_menu)
    await callback.message.answer(t(lang,"main_menu"), reply_markup=get_main_keyboard(lang, role))
    await callback.answer()


@router.callback_query(F.data.startswith("delprod:ask:"))
async def cb_delprod_ask(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer(); return
    lang = db.get_user_lang(callback.from_user.id)
    pid  = int(callback.data.split(":")[2])
    prod = db.get_product(pid)
    if not prod: await callback.answer(t(lang,"product_not_found"), show_alert=True); return
    from keyboards.inline import del_prod_confirm_keyboard
    cat = db.get_category_label(lang, prod["category"])
    text = t(lang,"del_product_confirm",
             name=prod["name"], code=prod["code"] or "-",
             category=cat, quantity=prod["quantity"])
    from utils.render import safe_edit_or_send
    await safe_edit_or_send(callback, text, del_prod_confirm_keyboard(lang, pid))
    await callback.answer()


@router.callback_query(F.data.startswith("delprod:confirm:"))
async def cb_delprod_confirm(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer(); return
    lang = db.get_user_lang(callback.from_user.id)
    pid  = int(callback.data.split(":")[2])
    prod = db.get_product(pid)
    if not prod: await callback.answer(); return
    name = prod["name"]
    db.delete_product_by_id(pid)
    from utils.render import safe_edit_or_send
    await safe_edit_or_send(callback, t(lang,"del_product_done", name=name))
    await callback.answer(t(lang,"del_product_done", name=name), show_alert=True)


@router.callback_query(F.data.startswith("delprod:cancel:"))
async def cb_delprod_cancel(callback: CallbackQuery):
    lang = db.get_user_lang(callback.from_user.id)
    pid  = int(callback.data.split(":")[2])
    prod = db.get_product(pid)
    if not prod: await callback.answer(); return
    from utils.render import send_product_detail
    await send_product_detail(callback, lang, prod, "catshow", admin=is_admin(callback.from_user.id))
    await callback.answer()
