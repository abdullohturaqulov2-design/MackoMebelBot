# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN         = os.getenv("BOT_TOKEN", "PUT_YOUR_BOT_TOKEN_HERE")
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY", "")
ADMIN_IDS  = [int(x) for x in os.getenv("ADMIN_IDS","").replace(" ","").split(",") if x.strip().isdigit()]

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
DATA_DIR      = os.path.join(BASE_DIR, "data")
DB_PATH       = os.path.join(DATA_DIR, "warehouse.db")
EXPORT_DIR    = os.path.join(DATA_DIR, "exports")
IMAGES_DIR    = os.path.join(DATA_DIR, "images")
NO_IMAGE_PATH = os.path.join(DATA_DIR, "no_image.png")

for _d in (DATA_DIR, EXPORT_DIR, IMAGES_DIR):
    os.makedirs(_d, exist_ok=True)

PAGE_SIZE = 5

ROLE_SUPERADMIN = "superadmin"
ROLE_ADMIN      = "admin"

DEFAULT_CATEGORIES = [
    ("akril",   "Akril",   "Акрил",  "Acrylic"),
    ("mdf",     "MDF",     "МДФ",    "MDF"),
    ("xdf",     "XDF",     "ХДФ",    "XDF"),
    ("laminat", "Laminat", "Ламинат","Laminate"),
    ("kromka",  "Kromka",  "Кромка", "Edge Banding"),
]
DEFAULT_SUBCATEGORIES = [
    ("akril","stalishnitsa",       "Stalishnitsa",       "Столешница",        "Countertop"),
    ("akril","kromka",             "Kromka",             "Кромка",            "Edge Banding"),
    ("akril","akril_mahsulotlari", "Akril mahsulotlari", "Изделия из акрила", "Acrylic products"),
]
