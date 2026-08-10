from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from locales.texts import t

def language_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🇺🇿 O'zbekcha"), KeyboardButton(text="🇷🇺 Русский")],
        [KeyboardButton(text="🇬🇧 English")],
    ], resize_keyboard=True)


def get_main_keyboard(lang: str, role: str) -> ReplyKeyboardMarkup:
    btn_scanner   = KeyboardButton(text=t(lang, "btn_scanner"))
    btn_macko_ai = KeyboardButton(text=t(lang, "btn_macko_ai"))
    
    if role in ("admin", "superadmin"):
        btn_excel = KeyboardButton(text=t(lang, "btn_get_excel"))
        return ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text=t(lang, "btn_warehouse"))],
            [KeyboardButton(text=t(lang, "btn_add")),      KeyboardButton(text=t(lang, "btn_remove"))],
            [KeyboardButton(text=t(lang, "btn_stats")),    KeyboardButton(text=t(lang, "btn_movement"))],
            [KeyboardButton(text=t(lang, "btn_history")),  KeyboardButton(text=t(lang, "btn_settings"))],
            [btn_scanner, btn_macko_ai],
            [btn_excel],
        ],resize_keyboard=True)
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=t(lang, "btn_warehouse"))],
        [KeyboardButton(text=t(lang, "btn_settings"))],
        [btn_scanner, btn_macko_ai],
    ], resize_keyboard=True)


def settings_keyboard(lang: str, role: str) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=t(lang, "btn_change_language"))]]
    if role in ("admin", "superadmin"):
        rows.append([KeyboardButton(text=t(lang, "btn_manage_cats"))])
    if role == "superadmin":
        rows.append([KeyboardButton(text=t(lang, "btn_manage_admins"))])
    rows.append([KeyboardButton(text=t(lang, "btn_back_main"))])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def cancel_only_keyboard(lang: str):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t(lang, "btn_back_main"))]],
        resize_keyboard=True
    )


def remove_keyboard():
    return ReplyKeyboardRemove()
