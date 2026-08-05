from config import ADMIN_IDS, ROLE_SUPERADMIN, ROLE_ADMIN

def is_superadmin(uid: int) -> bool:
    if uid in ADMIN_IDS: return True
    from database.db import get_user_role
    return get_user_role(uid) == ROLE_SUPERADMIN

def is_admin(uid: int) -> bool:
    if is_superadmin(uid): return True
    from database.db import get_user_role
    role = get_user_role(uid)
    return role in (ROLE_ADMIN, ROLE_SUPERADMIN)

def get_role_level(uid: int) -> str:
    """'superadmin' | 'admin' | 'user'"""
    if is_superadmin(uid): return "superadmin"
    if is_admin(uid):      return "admin"
    return "user"
