from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from database import db
from keyboards.reply import get_main_keyboard
from locales.texts import t
from states.states import AdminStates
from utils.access import get_role_level

router = Router()
LANG_BUTTONS = {"🇺🇿 O'zbekcha":"uz","🇷🇺 Русский":"ru","🇬🇧 English":"en"}

@router.message(F.text.in_(LANG_BUTTONS.keys()))
async def set_language(message: Message, state: FSMContext):
    lang = LANG_BUTTONS[message.text]
    uid  = message.from_user.id
    db.upsert_user(uid, message.from_user.username, message.from_user.full_name)
    db.set_user_lang(uid, lang)
    role = get_role_level(uid)
    await state.set_state(AdminStates.main_menu)
    await message.answer(t(lang,"language_set"))
    await message.answer(t(lang,"main_menu"), reply_markup=get_main_keyboard(lang, role))
