from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from database import db
from keyboards.reply import language_keyboard, get_main_keyboard
from locales.texts import t
from states.states import AdminStates
from utils.access import get_role_level

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    uid  = message.from_user.id
    db.upsert_user(uid, message.from_user.username, message.from_user.full_name)
    if not db.user_has_language(uid):
        await state.set_state(AdminStates.choosing_language)
        await message.answer(t("uz","choose_language"), reply_markup=language_keyboard())
        return
    lang = db.get_user_lang(uid)
    role = get_role_level(uid)
    await state.set_state(AdminStates.main_menu)
    await message.answer(t(lang,"main_menu"), reply_markup=get_main_keyboard(lang, role))

@router.message(Command("myid"))
async def cmd_myid(message: Message):
    lang = db.get_user_lang(message.from_user.id)
    await message.answer(t(lang,"myid_response", uid=message.from_user.id), parse_mode="HTML")
