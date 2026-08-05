# Ombor boshqaruv Telegram bot (aiogram 3)

Excel fayllar orqali mahsulot qo'shish/o'chirish, kategoriya bo'yicha ko'rish,
qidiruv va ko'p tillilikni qo'llab-quvvatlaydigan admin bot.

## 1. O'rnatish

```bash
cd warehouse_bot
python -m venv venv
source venv/bin/activate      # Windowsda: venv\Scripts\activate
pip install -r requirements.txt
```

`.env.example` faylini `.env` deb nomlang va to'ldiring:

```
BOT_TOKEN=BotFather bergan token
ADMIN_IDS=123456789,987654321
```

`ADMIN_IDS` bo'sh qoldirilsa — bot hamma foydalanuvchi uchun ochiq bo'ladi (test uchun).

## 2. Ishga tushirish

```bash
python bot.py
```

## 3. Excel fayl formati (mahsulot QO'SHISH uchun)

Birinchi qator — sarlavhalar. Ustunlar nomi (katta-kichik harf farqi yo'q):

| Nomi | Kodi | Kategoriya | Subkategoriya | Format | Qalinlik | Miqdor | Joylashuv | Rasm |
|------|------|-----------|----------------|--------|----------|--------|-----------|------|
| Red akril list | AKR-001 | akril | akril_mahsulotlari | 2800*2070 | 18mm | 25 | A-12 javon | |
| Oq stalishnitsa | ST-014 | akril | stalishnitsa | 3000*1200 | 38mm | 10 | B-3 | |
| Kromka oq 19/1 | KR-19-1 | kromka | 19/1 | | | 120 | Kromka javoni | |
| MDF plita | MDF-22 | mdf | | 2750*1830 | 16mm | 40 | Ombor-2 | |

**Kategoriya** qiymatlari: `akril`, `mdf`, `xdf`, `laminat`, `kromka` (majburiy).

**Subkategoriya**:
- `akril` uchun: `stalishnitsa`, `kromka`, `akril_mahsulotlari`
- `kromka` uchun: istalgan format matni, masalan `19/1`, `22/1` va h.k. — bular
  bot ichida avtomatik "kromka turlari" sifatida chiqadi.
- `mdf`, `xdf`, `laminat` uchun bo'sh qoldirilishi mumkin.

**Rasm** ustuniga — agar mahsulot rasmi serverdagi biror joyda saqlangan bo'lsa,
o'sha fayl **yo'lini** (path) yozing (masalan `images/akr001.jpg`). Bo'sh qoldirilsa,
mahsulot ochilganda "Rasm mavjud emas" degan placeholder rasm ko'rsatiladi.

## 4. Excel fayl formati (mahsulot O'CHIRISH uchun)

Faqat **Kodi** ustuni bo'lishi kifoya (boshqa ustunlar bo'lsa ham e'tiborga olinmaydi):

| Kodi |
|------|
| AKR-001 |
| ST-014 |

Bot shu kodlarga mos mahsulotlarni bazadan o'chiradi va natijada:
- "X ta mahsulot o'chirildi" xabari + inline tugmalar (o'chirilganlarni / qolganlarni ko'rish)
- O'chirilgan mahsulotlar ro'yxati **Excel va PDF** fayl ko'rinishida
- Bazada qolgan barcha mahsulotlar ro'yxati ham **Excel va PDF** fayl ko'rinishida

## 5. Botning ishlash mantig'i

1. `/start` — birinchi marta til tanlanadi (uz/ru/en), keyin asosiy menyu chiqadi.
2. Asosiy menyuda: **Ombordagi mahsulotlar**, **Mahsulot qo'shish**, **Mahsulot ayirish**, **Sozlamalar**.
3. **Mahsulot qo'shish** bosilsa — faqat "Asosiy menyu" tugmasi qoladi. Excel yuborilsa
   mahsulotlar bazaga qo'shiladi va natija + "Qo'shilganlarni ko'rish" tugmasi chiqadi.
   "Asosiy menyu" bosilsa — amal bekor qilinadi.
4. **Mahsulot ayirish** xuddi shunday, lekin o'chirish uchun.
5. **Ombordagi mahsulotlar** — kategoriya tanlanadi → (kerak bo'lsa subkategoriya) →
   mahsulotlar ro'yxati inline tugmalar bilan, sahifada maksimum 5 ta, "◀️ 1/3 ▶️" navigatsiya bilan.
   Mahsulot bosilsa — to'liq ma'lumot + rasm (yoki "rasm yo'q" placeholder) chiqadi.
6. Admin hech qanday tugma bosmasdan botga yozsa:
   - kategoriya nomi (masalan `akril`) — o'sha kategoriya ochiladi;
   - mahsulot nomi (masalan `Red`) — nomga mos qidiruv natijalari chiqadi;
   - mahsulot kodi — kodga mos mahsulot(lar) chiqadi;
   - o'lcham format (masalan `2800*2070`) — shu formatga mos mahsulotlar chiqadi;
   - qalinlik (masalan `18`, `18mm`, `1.8sm`) — shu qalinlikka mos mahsulotlar chiqadi;
   - kromka formati (masalan `19/1`) — shu formatdagi kromkalar chiqadi.
   Hech narsa topilmasa — "Mahsulot topilmadi" deb javob beradi.
7. **Sozlamalar** — tilni istalgan vaqt o'zgartirish mumkin.

## 6. Loyihaning tuzilishi

```
warehouse_bot/
├── bot.py                  # ishga tushirish nuqtasi
├── config.py                # sozlamalar (.env dan token/adminlar)
├── database/db.py           # SQLite bilan ishlash
├── locales/texts.py         # uz/ru/en matnlar
├── keyboards/                # reply va inline klaviaturalar
├── states/states.py         # FSM holatlari
├── handlers/                 # barcha bot logikasi
└── utils/                    # excel, pdf, rasm, keshlash, render funksiyalari
```

## 7. Eslatmalar

- Baza fayli avtomatik `data/warehouse.db` (SQLite) da yaratiladi.
- PDF fayllarda kirill harflar to'g'ri chiqishi uchun serverda DejaVuSans shrifti
  bo'lsa avtomatik ishlatiladi (`/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf`).
  Bo'lmasa standart shrift ishlatiladi — lotin (o'zbek) matn muammosiz chiqadi.
- Qidiruv/sahifalash holati vaqtinchalik xotirada saqlanadi — bot qayta ishga
  tushirilsa faqat navigatsiya "yangilanadi", mahsulotlar bazasi (SQLite) o'zgarmaydi.
