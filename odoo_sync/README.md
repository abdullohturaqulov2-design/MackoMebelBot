# Bot → Odoo Sinxronizatsiya

## Tuzilma
```
odoo_sync/
├── config.py       ← Sozlamalar (Odoo URL, login, bot DB yo'li)
├── odoo_client.py  ← Odoo XML-RPC klient
├── bot_db.py       ← Bot SQLite dan o'qish
├── sync.py         ← Sinxronizatsiya logikasi
├── run.py          ← Ishga tushirish
└── README.md
```

## O'rnatish

```bash
# Alohida kutubxona kerak emas — faqat Python 3.7+
cd odoo_sync
```

## Sozlash (config.py)

```python
ODOO_URL      = "https://sizning-odoo.com"
ODOO_DB       = "odoo_db_name"
ODOO_USER     = "admin@email.com"
ODOO_PASSWORD = "parol"
BOT_DB_PATH   = "../warehouse_bot/data/warehouse.db"
WAREHOUSE_LOCATION_ID = 8   # Odoo > Inventory > Locations > WH/Stock ID si
```

### WAREHOUSE_LOCATION_ID qanday topiladi?
Odoo da: `Settings → Technical → Locations`
"WH/Stock" ni toping → URL da ID ko'rinadi: `/web#id=8&model=stock.location`

## Ishga tushirish

```bash
# Bir marta sinxronlash
python run.py

# Har 30 daqiqada avtomatik (orqada ishlaydi)
python run.py --daemon &

# Termuxda fonda ishlash
nohup python run.py --daemon > /dev/null 2>&1 &
```

## Nima sinxronlanadi?

| Bot (SQLite)       | Odoo                        |
|--------------------|-----------------------------|
| categories         | product.category            |
| subcategories      | product.category (ichida)   |
| products (nomi)    | product.template            |
| products (kodi)    | default_code (internal ref) |
| products (narx)    | list_price + standard_price |
| products (miqdor)  | stock.quant                 |
| products (format)  | description                 |

## Sinxronizatsiya tartibi
```
Bot DB → Kategoriyalar → Mahsulotlar → Zaxira miqdorlari
```

## Logllar
Natijalar `sync.log` faylida saqlanadi.
