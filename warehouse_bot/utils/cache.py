# -*- coding: utf-8 -*-
"""
Har bir admin (user_id) uchun oxirgi qidiruv/ro'yxat holatini vaqtinchalik
xotirada saqlaydi. Bot qayta ishga tushsa tozalanadi - bu muammo emas,
chunki bular faqat navigatsiya (sahifalash) uchun kerak, asosiy ma'lumot
doim SQLite bazasida saqlanadi.
"""
from typing import Dict, List, Any

# {"field": "name"/"code"/"format"/"thickness"/"kromka_format", "value": str}
SEARCH_CACHE: Dict[int, Dict[str, Any]] = {}

# oxirgi excel orqali qo'shilgan mahsulotlar id lari
ADDED_CACHE: Dict[int, List[int]] = {}

# oxirgi excel orqali o'chirilgan mahsulotlar (to'liq row-dict holida, chunki DB dan o'chirilgan)
REMOVED_CACHE: Dict[int, List[Dict[str, Any]]] = {}

# o'chirishdan keyin bazada qolgan mahsulotlar id lari (report uchun)
REMAINING_CACHE: Dict[int, List[int]] = {}

# Excel tasdiqlash uchun vaqtinchalik kesh
PENDING_ADD_CACHE: dict = {}   # {user_id: [product_dicts]}
PENDING_DEL_CACHE: dict = {}   # {user_id: {"codes": [...], "path": "..."}}
PENDING_EXCEL_PATH: dict = {}  # {user_id: "/tmp/file.xlsx"}
