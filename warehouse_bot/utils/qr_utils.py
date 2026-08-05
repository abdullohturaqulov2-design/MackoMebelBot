# -*- coding: utf-8 -*-
"""
QR code generatsiya.
QR ichida: https://t.me/BOTUSERNAME?start=qr_KOD
Tashqi skaner → Telegram ochiladi → bot mahsulotni ko'rsatadi.
"""
import os, logging
logger = logging.getLogger(__name__)
QR_DIR = None

def init_qr_dir(data_dir: str):
    global QR_DIR
    QR_DIR = os.path.join(data_dir, "qr")
    os.makedirs(QR_DIR, exist_ok=True)

def _bot_username():
    return os.environ.get("BOT_USERNAME", "").strip().lstrip("@")

def qr_path_for(code: str, pid: int) -> str:
    name = (code or f"id_{pid}").replace("/","_").replace("\\","_")
    return os.path.join(QR_DIR, f"{name}.png")

def generate_qr(code: str, pid: int, name: str = "") -> str | None:
    if not QR_DIR:
        logger.warning("init_qr_dir chaqirilmagan!"); return None
    try:
        import qrcode
        from PIL import Image, ImageDraw

        username = _bot_username()
        safe_code = (code or f"id_{pid}").replace(" ", "_")

        # QR tarkibi: Telegram deep link yoki oddiy kod
        if username:
            data = f"https://t.me/{username}?start=qr_{safe_code}"
        else:
            data = safe_code

        qr = qrcode.QRCode(version=1,
                            error_correction=qrcode.constants.ERROR_CORRECT_M,
                            box_size=8, border=3)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#0d0d20", back_color="white").convert("RGB")

        # Kod yozuvini pastga qo'shish
        W, H = img.size
        canvas = Image.new("RGB", (W, H+34), "white")
        canvas.paste(img, (0,0))
        draw = ImageDraw.Draw(canvas)
        label = (code or f"#{pid}")[:24]
        bbox  = draw.textbbox((0,0), label)
        tw    = bbox[2]-bbox[0]
        draw.text(((W-tw)//2, H+8), label, fill="#0d0d20")

        path = qr_path_for(code, pid)
        canvas.save(path, "PNG")
        return path
    except ImportError:
        logger.error("pip install qrcode[pil]"); return None
    except Exception as e:
        logger.error(f"QR xato: {e}"); return None

def get_or_create_qr(product) -> str | None:
    if not QR_DIR: return None
    path = qr_path_for(product["code"] or "", product["id"])
    if os.path.exists(path): return path
    return generate_qr(product["code"] or "", product["id"], product.get("name",""))

def has_qr(product) -> bool:
    if not QR_DIR: return False
    return os.path.exists(qr_path_for(product["code"] or "", product["id"]))

def delete_qr(code: str, pid: int):
    if not QR_DIR: return
    try:
        p = qr_path_for(code, pid)
        if os.path.exists(p): os.remove(p)
    except Exception: pass
