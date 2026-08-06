import os, logging
logger = logging.getLogger(__name__)
QR_DIR = None

def init_qr_dir(data_dir):
    global QR_DIR
    QR_DIR = os.path.join(data_dir, "qr")
    os.makedirs(QR_DIR, exist_ok=True)

def _bot_username():
    return os.environ.get("BOT_USERNAME","").strip().lstrip("@")

def qr_path_for(code, pid):
    name=(code or f"id_{pid}").replace("/","_").replace("\\","_")
    return os.path.join(QR_DIR, f"{name}.png")

def generate_qr(code, pid, name=""):
    if not QR_DIR: return None
    try:
        import qrcode
        from PIL import Image, ImageDraw

        username=_bot_username()
        safe=( code or f"id_{pid}" ).replace(" ","_")
        data=f"https://t.me/{username}?start=qr_{safe}" if username else safe

        qr=qrcode.QRCode(version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10, border=4)
        qr.add_data(data); qr.make(fit=True)

        # ✅ QORA rang — jsQR aniq o'qiydi
        img=qr.make_image(fill_color="black", back_color="white").convert("RGB")
        W,H=img.size
        canvas=Image.new("RGB",(W,H+36),"white")
        canvas.paste(img,(0,0))
        draw=ImageDraw.Draw(canvas)
        label=(code or f"#{pid}")[:22]
        bbox=draw.textbbox((0,0),label)
        draw.text(((W-(bbox[2]-bbox[0]))//2, H+9), label, fill="black")
        path=qr_path_for(code,pid)
        canvas.save(path,"PNG"); return path
    except ImportError:
        logger.error("pip install qrcode[pil]"); return None
    except Exception as e:
        logger.error(f"QR xato: {e}"); return None

def get_or_create_qr(product):
    if not QR_DIR: return None
    path=qr_path_for(product["code"] or "", product["id"])
    if os.path.exists(path): return path
    return generate_qr(product["code"] or "", product["id"], product.get("name",""))

def has_qr(product):
    if not QR_DIR: return False
    return os.path.exists(qr_path_for(product["code"] or "", product["id"]))

def delete_qr(code, pid):
    if not QR_DIR: return
    try:
        p=qr_path_for(code,pid)
        if os.path.exists(p): os.remove(p)
    except: pass
