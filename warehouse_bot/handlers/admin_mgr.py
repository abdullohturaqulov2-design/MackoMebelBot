# -*- coding: utf-8 -*-
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import db
from config import ADMIN_IDS, ROLE_SUPERADMIN, ROLE_ADMIN
from locales.texts import TEXTS, t
from keyboards.inline import admin_mgr_keyboard, admin_confirm_keyboard
from keyboards.reply import get_main_keyboard, cancel_only_keyboard
from states.states import AdminStates
from utils.access import is_superadmin, get_role_level
from utils.render import delete_msg

router = Router()
def _all(k): return {TEXTS[l][k] for l in TEXTS}


@router.message(F.text.in_(_all("btn_manage_admins")))
async def open_admin_mgr(message: Message, state: FSMContext):
    uid = message.from_user.id
    if not is_superadmin(uid): return
    await delete_msg(message)
    lang  = db.get_user_lang(uid)
    admins = db.get_admin_users()
    await state.set_state(AdminStates.admin_mgr)
    await message.answer(
        t(lang, "admin_mgr_title"),
        reply_markup=admin_mgr_keyboard(lang, admins, ADMIN_IDS),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admgr:list")
async def cb_admin_list(callback: CallbackQuery, state: FSMContext):
    uid  = callback.from_user.id
    if not is_superadmin(uid): await callback.answer(); return
    lang   = db.get_user_lang(uid)
    admins = db.get_admin_users()
    await state.set_state(AdminStates.admin_mgr)
    from utils.render import safe_edit_or_send
    await safe_edit_or_send(
        callback,
        t(lang, "admin_mgr_title"),
        admin_mgr_keyboard(lang, admins, ADMIN_IDS)
    )
    await callback.answer()


@router.callback_query(F.data == "admgr:add")
async def cb_admin_add(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    if not is_superadmin(uid): await callback.answer(); return
    lang = db.get_user_lang(uid)
    await state.set_state(AdminStates.waiting_admin_id)
    await callback.message.answer(
        t(lang, "admin_add_prompt"),
        parse_mode="HTML",
        reply_markup=cancel_only_keyboard(lang)
    )
    await callback.answer()


@router.message(AdminStates.waiting_admin_id, F.text)
async def got_admin_id(message: Message, state: FSMContext):
    uid  = message.from_user.id
    lang = db.get_user_lang(uid)

    # Bekor qilish
    cancel_texts = {TEXTS[l].get("btn_back_main","") for l in TEXTS}
    cancel_texts |= {TEXTS[l].get("btn_cancel_add","") for l in TEXTS}
    if message.text.strip() in cancel_texts:
        role = get_role_level(uid)
        await state.set_state(AdminStates.main_menu)
        await message.answer(t(lang,"action_cancelled"),
                             reply_markup=get_main_keyboard(lang, role))
        return

    text = message.text.strip()
    try:
        target_uid = int(text)
    except ValueError:
        await message.answer(t(lang, "admin_id_invalid"))
        return

    if target_uid in ADMIN_IDS:
        await message.answer(f"⚠️ Bu superadmin — o'zgartirish mumkin emas.")
        return

    # Foydalanuvchi bazada bormi?
    target_lang = db.get_user_lang(target_uid)
    if not db.user_has_language(target_uid):
        await message.answer(t(lang, "admin_not_found_db"))
        return

    # Tasdiqlash so'rash
    user_info = db.get_admin_users()
    name = str(target_uid)
    for u in db.get_admin_users():
        if u["user_id"] == target_uid:
            name = u["full_name"] or u["username"] or str(target_uid)
            break
    else:
        # Barcha userlardan qidirish
        try:
            conn = db.get_conn(); c = conn.cursor()
            c.execute("SELECT full_name, username FROM users WHERE user_id=?", (target_uid,))
            row = c.fetchone(); conn.close()
            if row:
                name = row["full_name"] or row["username"] or str(target_uid)
        except Exception:
            pass

    await state.update_data(target_uid=target_uid)
    await message.answer(
        t(lang, "admin_confirm", uid=target_uid, name=name),
        parse_mode="HTML",
        reply_markup=admin_confirm_keyboard(lang, target_uid)
    )


@router.callback_query(F.data.startswith("admgr:confirm:"))
async def cb_admin_confirm(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    if not is_superadmin(uid): await callback.answer(); return
    lang       = db.get_user_lang(uid)
    target_uid = int(callback.data.split(":")[2])

    db.set_user_role(target_uid, ROLE_ADMIN)
    await state.set_state(AdminStates.admin_mgr)

    admins = db.get_admin_users()
    from utils.render import safe_edit_or_send
    await safe_edit_or_send(
        callback,
        t(lang, "admin_added", uid=target_uid) + "\n\n" + t(lang, "admin_mgr_title"),
        admin_mgr_keyboard(lang, admins, ADMIN_IDS)
    )
    await callback.answer(t(lang, "admin_added", uid=target_uid), show_alert=True)


@router.callback_query(F.data.startswith("admgr:del:"))
async def cb_admin_del(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    if not is_superadmin(uid): await callback.answer(); return
    lang       = db.get_user_lang(uid)
    target_uid = int(callback.data.split(":")[2])

    if target_uid in ADMIN_IDS:
        await callback.answer(t(lang, "admin_cannot_remove"), show_alert=True)
        return

    db.set_user_role(target_uid, None)
    admins = db.get_admin_users()
    from utils.render import safe_edit_or_send
    await safe_edit_or_send(
        callback,
        t(lang, "admin_removed", uid=target_uid) + "\n\n" + t(lang, "admin_mgr_title"),
        admin_mgr_keyboard(lang, admins, ADMIN_IDS)
    )
    await callback.answer(t(lang, "admin_removed", uid=target_uid), show_alert=True)


@router.message(F.text.in_(_all("btn_manage_admins")), AdminStates.admin_mgr)
async def noop(message: Message): pass
