# -*- coding: utf-8 -*-
import os, uuid
from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext

from database import db
from keyboards.reply import cancel_only_keyboard, get_main_keyboard
from keyboards.inline import removed_report_keyboard, excel_del_confirm_keyboard
from locales.texts import TEXTS, t
from states.states import AdminStates, ExcelConfirmStates
from utils.access import is_admin, get_role_level
from utils.excel_utils import read_delete_codes_from_excel, export_products_to_excel
from utils.pdf_utils import export_products_to_pdf
from utils.cache import REMOVED_CACHE, REMAINING_CACHE, PENDING_DEL_CACHE, PENDING_EXCEL_PATH
from config import DATA_DIR, EXPORT_DIR

router = Router()
def _all(k): return {TEXTS[l][k] for l in TEXTS}


@router.message(AdminStates.main_menu, F.text.in_(_all("btn_remove")))
async def start_remove(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    from utils.render import delete_msg; await delete_msg(message)
    lang = db.get_user_lang(message.from_user.id)
    await state.set_state(AdminStates.waiting_excel_remove)
    await message.answer(t(lang,"remove_prompt"), parse_mode="HTML",
                         reply_markup=cancel_only_keyboard(lang))


@router.message(AdminStates.waiting_excel_remove, F.document)
async def process_remove_excel(message: Message, state: FSMContext, bot):
    if not is_admin(message.from_user.id): return
    lang = db.get_user_lang(message.from_user.id)
    if not (message.document.file_name or "").lower().endswith((".xlsx",".xlsm")):
        await message.answer(t(lang,"not_excel_file")); return

    await message.answer(t(lang,"processing_file"))
    tmp  = os.path.join(DATA_DIR,"tmp"); os.makedirs(tmp, exist_ok=True)
    path = os.path.join(tmp, f"del_{uuid.uuid4().hex}.xlsx")
    fi   = await bot.get_file(message.document.file_id)
    await bot.download_file(fi.file_path, destination=path)

    codes = read_delete_codes_from_excel(path)
    uid   = message.from_user.id
    PENDING_DEL_CACHE[uid]  = codes
    PENDING_EXCEL_PATH[uid] = path

    # Qaysi mahsulotlar o'chirilishini ko'rsat
    will_delete = []
    for code in codes:
        conn = db.get_conn(); c = conn.cursor()
        c.execute("SELECT * FROM products WHERE code=?", (code,))
        row = c.fetchone(); conn.close()
        if row: will_delete.append(row)

    if not will_delete:
        await message.answer(t(lang,"removed_none"))
        role = get_role_level(uid)
        await state.set_state(AdminStates.main_menu)
        await message.answer(t(lang,"main_menu"), reply_markup=get_main_keyboard(lang,role))
        return

    preview = ""
    for p in will_delete[:5]:
        preview += f"  • {p['name']} ({p['code'] or '-'})\n"
    if len(will_delete) > 5:
        preview += f"  ... va yana {len(will_delete)-5} ta\n"

    await message.answer(
        t(lang,"excel_del_confirm", count=len(will_delete), preview=preview.strip()),
        parse_mode="HTML",
        reply_markup=excel_del_confirm_keyboard(lang)
    )
    await state.set_state(ExcelConfirmStates.confirming_del)


@router.callback_query(F.data=="excdel:confirm", ExcelConfirmStates.confirming_del)
async def excdel_confirm(callback, state: FSMContext):
    lang = db.get_user_lang(callback.from_user.id)
    uid  = callback.from_user.id
    codes = PENDING_DEL_CACHE.get(uid, [])

    removed = []
    for code in codes:
        r = db.delete_product_by_code(code)
        if r: removed.append(db.row_to_dict(r))

    PENDING_DEL_CACHE.pop(uid, None)

    if not removed:
        await callback.message.answer(t(lang,"removed_none"))
    else:
        REMOVED_CACHE[uid]   = removed
        remaining            = db.get_all_products()
        REMAINING_CACHE[uid] = [r["id"] for r in remaining]

        await callback.message.answer(
            t(lang,"removed_count", count=len(removed)),
            reply_markup=removed_report_keyboard(lang))

        s  = uuid.uuid4().hex[:8]
        rx = os.path.join(EXPORT_DIR, f"ochirilgan_{s}.xlsx")
        rp = os.path.join(EXPORT_DIR, f"ochirilgan_{s}.pdf")
        kx = os.path.join(EXPORT_DIR, f"qolgan_{s}.xlsx")
        kp = os.path.join(EXPORT_DIR, f"qolgan_{s}.pdf")
        kd = [db.row_to_dict(r) for r in remaining]

        export_products_to_excel(removed, rx, "Ochirilgan")
        export_products_to_pdf(removed,   rp, "O'chirilgan mahsulotlar")
        export_products_to_excel(kd, kx, "Qolgan")
        export_products_to_pdf(kd,   kp, "Qolgan mahsulotlar")

        await callback.message.answer_document(FSInputFile(rx), caption=f"🗑 {t(lang,'btn_view_removed')}")
        await callback.message.answer_document(FSInputFile(rp))
        await callback.message.answer_document(FSInputFile(kx), caption=f"📦 {t(lang,'btn_view_remaining')}")
        await callback.message.answer_document(FSInputFile(kp))

    role = get_role_level(uid)
    await state.set_state(AdminStates.main_menu)
    await callback.message.answer(t(lang,"main_menu"), reply_markup=get_main_keyboard(lang,role))
    await callback.answer()


@router.callback_query(F.data=="excdel:edit", ExcelConfirmStates.confirming_del)
async def excdel_edit(callback, state: FSMContext):
    lang = db.get_user_lang(callback.from_user.id)
    uid  = callback.from_user.id
    path = PENDING_EXCEL_PATH.get(uid)
    if path and os.path.exists(path):
        await callback.message.answer_document(
            FSInputFile(path), caption=t(lang,"excel_edit_hint"))
    await state.set_state(ExcelConfirmStates.waiting_new_del_excel)
    await callback.answer()


@router.message(ExcelConfirmStates.waiting_new_del_excel, F.document)
async def excdel_new_file(message: Message, state: FSMContext, bot):
    if not is_admin(message.from_user.id): return
    await state.set_state(AdminStates.waiting_excel_remove)
    await process_remove_excel(message, state, bot)


@router.callback_query(F.data=="excdel:cancel", ExcelConfirmStates.confirming_del)
async def excdel_cancel(callback, state: FSMContext):
    lang = db.get_user_lang(callback.from_user.id)
    uid  = callback.from_user.id
    PENDING_DEL_CACHE.pop(uid, None)
    role = get_role_level(uid)
    await state.set_state(AdminStates.main_menu)
    await callback.message.answer(t(lang,"action_cancelled"),
                                  reply_markup=get_main_keyboard(lang,role))
    await callback.answer()


@router.message(AdminStates.waiting_excel_remove, F.text)
async def process_remove_manual(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    query = message.text.strip()
    if not query: return
    from handlers.manual_delete import start_manual_delete
    await start_manual_delete(message, state, query)
