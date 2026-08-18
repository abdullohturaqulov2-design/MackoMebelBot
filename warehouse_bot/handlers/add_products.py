# -*- coding: utf-8 -*-
import os, uuid
from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext

from database import db
from keyboards.reply import cancel_only_keyboard, get_main_keyboard
from keyboards.inline import added_view_keyboard, excel_confirm_keyboard
from locales.texts import TEXTS, t
from states.states import AdminStates, ExcelConfirmStates
from utils.access import is_admin, get_role_level
from utils.excel_utils import read_products_from_excel
from utils.cache import ADDED_CACHE, PENDING_ADD_CACHE, PENDING_EXCEL_PATH
from config import DATA_DIR

router = Router()
def _all(k): return {TEXTS[l][k] for l in TEXTS if k in TEXTS[l]}


@router.message(AdminStates.main_menu, F.text.in_(_all("btn_add")))
async def start_add(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    from utils.render import delete_msg; await delete_msg(message)
    lang = db.get_user_lang(message.from_user.id)
    await state.set_state(AdminStates.waiting_excel_add)
    await message.answer(t(lang,"add_prompt"), parse_mode="HTML",
                         reply_markup=cancel_only_keyboard(lang))


@router.message(AdminStates.waiting_excel_add, F.document)
async def process_add_excel(message: Message, state: FSMContext, bot):
    if not is_admin(message.from_user.id): return
    lang = db.get_user_lang(message.from_user.id)
    if not (message.document.file_name or "").lower().endswith((".xlsx",".xlsm")):
        await message.answer(t(lang,"not_excel_file")); return

    await message.answer(t(lang,"processing_file"))
    tmp  = os.path.join(DATA_DIR,"tmp"); os.makedirs(tmp, exist_ok=True)
    path = os.path.join(tmp, f"add_{uuid.uuid4().hex}.xlsx")
    fi   = await bot.get_file(message.document.file_id)
    await bot.download_file(fi.file_path, destination=path)

    products, errors = read_products_from_excel(path)
    uid = message.from_user.id
    PENDING_ADD_CACHE[uid] = products
    PENDING_EXCEL_PATH[uid] = path

    if not products:
        err_text = "\n".join(errors[:5]) if errors else "-"
        await message.answer(t(lang,"added_none", errors=err_text))
        role = get_role_level(uid)
        await state.set_state(AdminStates.main_menu)
        await message.answer(t(lang,"main_menu"), reply_markup=get_main_keyboard(lang,role))
        return

    preview = ""
    for p in products[:5]:
        preview += f"  • {p['name']} ({p.get('code','') or '-'})\n"
    if len(products) > 5:
        preview += f"  ... va yana {len(products)-5} ta\n"
    if errors:
        preview += f"\n⚠️ {len(errors)} ta qator o'tkazildi"

    await message.answer(
        t(lang,"excel_confirm", count=len(products), preview=preview.strip()),
        parse_mode="HTML",
        reply_markup=excel_confirm_keyboard(lang))
    await state.set_state(ExcelConfirmStates.confirming_add)


@router.callback_query(F.data=="excadd:confirm", ExcelConfirmStates.confirming_add)
async def excadd_confirm(callback, state: FSMContext):
    lang = db.get_user_lang(callback.from_user.id)
    uid  = callback.from_user.id
    products = PENDING_ADD_CACHE.get(uid, [])
    if not products:
        await callback.answer(); return

    added_list, updated_list = [], []

    for p in products:
        code = p.get("code","")
        existing = db.get_product_by_code(code) if code else None

        if existing:
            # Mavjud: miqdor QO'SHILADI, ma'lumotlar yangilanadi
            old_qty = float(existing["quantity"] or 0)
            new_qty = old_qty + float(p.get("quantity",0) or 0)
            from database.db import get_conn
            conn = get_conn(); c = conn.cursor()
            c.execute("""UPDATE products SET
                name=?, subcategory=?, format_size=?, thickness=?,
                quantity=?, price=?, location=?
                WHERE code=?""",
                (p["name"],
                 (p.get("subcategory","") or "").lower().strip() or None,
                 p.get("format_size",""), p.get("thickness",""),
                 new_qty, p.get("price",0), p.get("location",""),
                 code))
            conn.commit(); conn.close()
            updated_list.append({
                "name": p["name"], "code": code,
                "old_qty": old_qty, "new_qty": new_qty
            })
        else:
            # Yangi mahsulot
            pid = db.add_product(
                name=p["name"], code=code,
                category=p["category"], subcategory=p.get("subcategory",""),
                format_size=p.get("format_size",""), thickness=p.get("thickness",""),
                quantity=p.get("quantity",0), location=p.get("location",""),
                image_path=p.get("image_path"), price=p.get("price",0))
            added_list.append({"name": p["name"], "code": code, "id": pid})

    PENDING_ADD_CACHE.pop(uid, None)

    # Batafsil natija
    result = "📊 <b>Natija:</b>\n\n"
    if added_list:
        result += f"✅ <b>Yangi qo'shildi ({len(added_list)} ta):</b>\n"
        for a in added_list[:10]:
            result += f"  • {a['name']} ({a['code'] or '-'})\n"
        if len(added_list) > 10:
            result += f"  ... va yana {len(added_list)-10} ta\n"
        result += "\n"

    if updated_list:
        result += f"🔄 <b>Yangilandi ({len(updated_list)} ta):</b>\n"
        for u in updated_list[:10]:
            result += f"  • {u['name']}: {int(u['old_qty'])} → {int(u['new_qty'])} ta\n"
        if len(updated_list) > 10:
            result += f"  ... va yana {len(updated_list)-10} ta\n"

    await callback.message.answer(result, parse_mode="HTML")
    ADDED_CACHE[uid] = [a["id"] for a in added_list]

    role = get_role_level(uid)
    await state.set_state(AdminStates.main_menu)
    await callback.message.answer(t(lang,"main_menu"),
                                  reply_markup=get_main_keyboard(lang,role))
    await callback.answer()


@router.callback_query(F.data=="excadd:edit", ExcelConfirmStates.confirming_add)
async def excadd_edit(callback, state: FSMContext):
    lang = db.get_user_lang(callback.from_user.id)
    uid  = callback.from_user.id
    path = PENDING_EXCEL_PATH.get(uid)
    if path and os.path.exists(path):
        await callback.message.answer_document(
            FSInputFile(path), caption=t(lang,"excel_edit_hint"))
    await state.set_state(ExcelConfirmStates.waiting_new_excel)
    await callback.answer()

@router.message(ExcelConfirmStates.waiting_new_excel, F.document)
async def excadd_new_file(message: Message, state: FSMContext, bot):
    if not is_admin(message.from_user.id): return
    await state.set_state(AdminStates.waiting_excel_add)
    await process_add_excel(message, state, bot)

@router.callback_query(F.data=="excadd:cancel", ExcelConfirmStates.confirming_add)
async def excadd_cancel(callback, state: FSMContext):
    lang = db.get_user_lang(callback.from_user.id)
    uid  = callback.from_user.id
    PENDING_ADD_CACHE.pop(uid, None)
    role = get_role_level(uid)
    await state.set_state(AdminStates.main_menu)
    await callback.message.answer(t(lang,"action_cancelled"),
                                  reply_markup=get_main_keyboard(lang,role))
    await callback.answer()

@router.message(AdminStates.waiting_excel_add, F.text)
async def process_add_manual(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    name = message.text.strip()
    if not name: return
    from handlers.manual_add import start_manual_add
    await start_manual_add(message, state, name)
