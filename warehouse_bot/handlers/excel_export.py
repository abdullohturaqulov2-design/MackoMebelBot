# -*- coding: utf-8 -*-
"""
"📊 Excel olish" tugmasi bosilganda bazadagi barcha
mahsulotlarni Excel fayl qilib yuboradi.
"""
import os, uuid
from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from database import db
from locales.texts import TEXTS, t
from utils.access import is_admin
from utils.render import delete_msg
from config import DATA_DIR

router = Router()
EXPORT_DIR = os.path.join(DATA_DIR, "exports")
os.makedirs(EXPORT_DIR, exist_ok=True)

def _all(k): return {TEXTS[l].get(k,"") for l in TEXTS} - {""}


@router.message(F.text.in_(_all("btn_get_excel")))
async def send_excel(message: Message):
    uid  = message.from_user.id
    lang = db.get_user_lang(uid)

    if not is_admin(uid):
        await message.answer("⚠️ Faqat adminlar uchun.")
        return

    await delete_msg(message)
    wait = await message.answer("⏳ Excel tayyorlanmoqda...")

    try:
        products = db.get_all_products()
        if not products:
            await wait.delete()
            await message.answer("⚠️ Bazada mahsulot yo'q.")
            return

        from utils.excel_utils import export_products_to_excel
        path = os.path.join(EXPORT_DIR, f"mahsulotlar_{uuid.uuid4().hex[:6]}.xlsx")
        export_products_to_excel([dict(p) for p in products], path, "Mahsulotlar")

        await wait.delete()
        await message.answer_document(
            FSInputFile(path, filename="macko_mahsulotlar.xlsx"),
            caption=(
                f"📊 <b>Barcha mahsulotlar</b>\n"
                f"📦 Jami: <b>{len(products)}</b> ta\n"
                f"📅 Sana: {__import__('datetime').datetime.now().strftime('%d.%m.%Y %H:%M')}"
            ),
            parse_mode="HTML"
        )
        # Faylni o'chirish (diskni tozalash)
        try: os.remove(path)
        except: pass

    except Exception as e:
        await wait.delete()
        await message.answer(f"❌ Xato: {e}")
