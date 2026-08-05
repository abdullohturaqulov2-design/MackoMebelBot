from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    choosing_language = State()
    main_menu         = State()
    settings_menu     = State()
    cat_mgr           = State()       # ← QO'SHING
    admin_mgr         = State()       # ← QO'SHING
    waiting_admin_id  = State()       # ← QO'SHING
    waiting_excel_add    = State()
    waiting_excel_remove = State()

class CategoryStates(StatesGroup):
    # Kategoriya qo'shish
    adding_cat_slug = State()
    adding_cat_uz   = State()
    adding_cat_ru   = State()
    adding_cat_en   = State()
    # Subkategoriya qo'shish
    adding_sub_slug = State()
    adding_sub_uz   = State()
    adding_sub_ru   = State()
    adding_sub_en   = State()

class MovementStates(StatesGroup):
    searching   = State()   # mahsulot qidirish
    choosing_type = State() # IN yoki OUT
    entering_qty  = State()
    entering_note = State()
    setting_min   = State() # min_quantity belgilash

class AdminMgrStates(StatesGroup):
    waiting_user_id = State()

class ManualAddStates(StatesGroup):
    waiting_code        = State()
    waiting_category    = State()
    waiting_subcategory = State()
    waiting_format      = State()
    waiting_thickness   = State()
    waiting_price       = State()
    waiting_quantity    = State()
    waiting_location    = State()
    waiting_image       = State()

class ManualDelStates(StatesGroup):
    searching   = State()   # kod yoki nom yozilishini kutish
    confirming  = State()   # bitta topilganda tasdiqlash

class ManualAddEditStates(StatesGroup):
    choosing_field  = State()   # qaysi maydonni tahrirlash
    editing_value   = State()   # yangi qiymat kiritish
    editing_category   = State()
    editing_subcategory = State()
    # Inline kategoriya yaratish (manual add ichida)
    new_cat_slug = State(); new_cat_uz = State()
    new_cat_ru   = State(); new_cat_en = State()
    new_sub_slug = State(); new_sub_uz = State()
    new_sub_ru   = State(); new_sub_en = State()

class ExcelConfirmStates(StatesGroup):
    confirming_add    = State()   # Excel qo'shishni tasdiqlash
    waiting_new_excel = State()   # Tahrirlangan Excel kutish
    confirming_del    = State()   # Excel o'chirishni tasdiqlash
    waiting_new_del_excel = State()

class PhotoStates(StatesGroup):
    waiting_photo = State()
