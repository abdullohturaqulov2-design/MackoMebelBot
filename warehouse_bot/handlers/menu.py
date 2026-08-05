from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from database import db
from keyboards.reply import get_main_keyboard, settings_keyboard, language_keyboard
from locales.texts import TEXTS, t
from states.states import AdminStates
from utils.access import get_role_level
from utils.render import delete_msg

router = Router()
def _all(key): return {TEXTS[l][key] for l in TEXTS}

@router.message(F.text.in_(_all("btn_back_main")))
async def back_to_main(message: Message, state: FSMContext):
    await delete_msg(message)
    uid = message.from_user.id; lang = db.get_user_lang(uid); role = get_role_level(uid)
    await state.set_state(AdminStates.main_menu)
    await message.answer(t(lang,"main_menu"), reply_markup=get_main_keyboard(lang,role))

@router.message(F.text.in_(_all("btn_settings")))
async def open_settings(message: Message, state: FSMContext):
    await delete_msg(message)
    uid = message.from_user.id; lang = db.get_user_lang(uid); role = get_role_level(uid)
    await state.set_state(AdminStates.settings_menu)
    await message.answer(t(lang,"settings_menu"), reply_markup=settings_keyboard(lang,role))

@router.message(F.text.in_(_all("btn_change_language")))
async def change_lang(message: Message, state: FSMContext):
    await delete_msg(message)
    lang = db.get_user_lang(message.from_user.id)
    await state.set_state(AdminStates.choosing_language)
    await message.answer(t(lang,"select_lang_prompt"), reply_markup=language_keyboard())
