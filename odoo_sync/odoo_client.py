import xmlrpc.client, logging
from config import ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD

logger  = logging.getLogger(__name__)
_uid    = None
_models = None

def connect():
    global _uid, _models
    try:
        common  = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common", allow_none=True)
        _uid    = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
        _models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object", allow_none=True)
        logger.info(f"Odoo ulandi. UID={_uid}")
        return bool(_uid)
    except Exception as e:
        logger.error(f"Odoo ulanmadi: {e}"); return False

def call(model, method, args=None, kw=None):
    if not _uid: raise ConnectionError("connect() ni chaqiring")
    return _models.execute_kw(ODOO_DB, _uid, ODOO_PASSWORD, model, method, args or [[]], kw or {})

def search(model, domain, fields=None, limit=None):
    kw = {}
    if fields: kw["fields"] = fields
    if limit:  kw["limit"]  = limit
    ids = call(model, "search", [domain])
    return call(model, "read", [ids], kw) if ids else []

def find_one(model, domain, fields=None):
    r = search(model, domain, fields=fields, limit=1)
    return r[0] if r else None

def create(model, vals):
    return call(model, "create", [[vals]])

def write(model, rid, vals):
    return call(model, "write", [[rid], vals])

def create_or_update(model, domain, vals):
    ex = find_one(model, domain, fields=["id"])
    if ex: write(model, ex["id"], vals); return ex["id"], "updated"
    return create(model, vals), "created"
