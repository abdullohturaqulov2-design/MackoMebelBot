# -*- coding: utf-8 -*-
import os
from PIL import Image, ImageDraw, ImageFont
from config import NO_IMAGE_PATH


def ensure_no_image_placeholder():
    if os.path.exists(NO_IMAGE_PATH):
        return NO_IMAGE_PATH
    img = Image.new("RGB", (600, 400), color=(230, 230, 230))
    draw = ImageDraw.Draw(img)
    text = "Rasm mavjud emas"
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 32)
    except Exception:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((600 - w) / 2, (400 - h) / 2), text, fill=(120, 120, 120), font=font)
    # ramka
    draw.rectangle([10, 10, 590, 390], outline=(180, 180, 180), width=3)
    img.save(NO_IMAGE_PATH)
    return NO_IMAGE_PATH
