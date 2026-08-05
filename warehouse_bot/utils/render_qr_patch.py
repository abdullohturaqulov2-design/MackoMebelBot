"""
utils/render.py dagi send_product_detail funksiyasiga
QR code qo'shish uchun patch.

send_product_detail funksiyasini topib, oxiriga quyidagini qo'shing:

    # QR code ham yuborish
    try:
        from utils.qr_utils import get_or_create_qr
        qr_path = get_or_create_qr(prod)
        if qr_path and os.path.exists(qr_path):
            await msg.answer_photo(
                photo=FSInputFile(qr_path),
                caption=f"📦 QR Code: <code>{prod['code'] or '#'+str(prod['id'])}</code>",
                parse_mode="HTML"
            )
    except Exception:
        pass
"""

# Bu to'liq yangi send_product_detail funksiyasi
NEW_SEND_PRODUCT_DETAIL = '''
async def send_product_detail(target, lang, prod, back_cb, admin=False):
    text     = format_detail(lang, prod)
    img      = prod["image_path"] if prod["image_path"] else None
    has_photo= bool(img and os.path.exists(img))
    kb       = (product_detail_admin_keyboard(lang, prod["id"], back_cb, has_photo=has_photo)
                if admin else product_detail_back_keyboard(lang, back_cb))
    msg      = target.message if isinstance(target, CallbackQuery) else target
    photo    = FSInputFile(img) if has_photo else FSInputFile(ensure_no_image_placeholder())

    if isinstance(target, CallbackQuery):
        await delete_msg(target.message)

    await msg.answer_photo(photo=photo, caption=text,
                           reply_markup=kb, parse_mode="HTML")

    # QR code
    try:
        from utils.qr_utils import get_or_create_qr
        qr_path = get_or_create_qr(prod)
        if qr_path and os.path.exists(qr_path):
            code_text = prod["code"] or f"#{prod['id']}"
            await msg.answer_photo(
                photo=FSInputFile(qr_path),
                caption=f"📦 QR Code: <code>{code_text}</code>",
                parse_mode="HTML"
            )
    except Exception:
        pass
'''
print(NEW_SEND_PRODUCT_DETAIL)
