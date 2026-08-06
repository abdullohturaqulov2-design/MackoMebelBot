# -*- coding: utf-8 -*-
"""
AI orqali rasm tahlili — ishonchli, pullik API uchun optimallashtirilgan.
Retry: 3 marta. Rate limit bo'lsa kutib qayta urinadi.
Provayderlar: Gemini (arzon) > OpenAI (eng aniq) > Claude
"""
import os, json, base64, logging, time, urllib.request, urllib.error
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

PROMPT = """Bu rasm omborxona uchun. Faqat JSON qaytaring, boshqa hech narsa yo'q:
{
  "name_keywords": ["mahsulot nomiga oid 3-6 ta kalit so'z"],
  "category": "faqat bulardan: akril, mdf, xdf, laminat, kromka, zapchastlar — yoki null",
  "format": "masalan 2800*2070 yoki null",
  "thickness": "masalan 18mm yoki null",
  "color": "rang o'zbekcha",
  "description": "1 jumla o'zbekcha tavsif"
}"""

def _load_env():
    try:
        from dotenv import load_dotenv
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        load_dotenv(os.path.join(root, ".env"), override=True)
    except Exception:
        pass

def _get_provider() -> Tuple[Optional[str], Optional[str]]:
    _load_env()
    for env, prov in [
        ("GEMINI_API_KEY","gemini"),("GOOGLE_API_KEY","gemini"),
        ("OPENAI_API_KEY","openai"),("ANTHROPIC_API_KEY","anthropic"),
    ]:
        k = os.environ.get(env,"").strip()
        if k: return k, prov
    return None, None

def _b64(path):
    with open(path,"rb") as f: return base64.b64encode(f.read()).decode()

def _mime(path):
    ext = os.path.splitext(path)[1].lower().strip(".")
    return {"jpg":"image/jpeg","jpeg":"image/jpeg","png":"image/png","webp":"image/webp"}.get(ext,"image/jpeg")

def _post(url, payload, headers):
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode())

def _parse(raw):
    raw = raw.strip()
    if "```" in raw:
        for p in raw.split("```"):
            p = p.strip()
            if p.startswith("json"): p = p[4:].strip()
            if p.startswith("{"): raw = p; break
    result = json.loads(raw)
    for key in ("name_keywords","category","color","description"):
        if key not in result: result[key] = [] if key=="name_keywords" else None
    return result

def _gemini(key, path):
    r = _post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}",
        {"contents":[{"parts":[{"text":PROMPT},{"inline_data":{"mime_type":_mime(path),"data":_b64(path)}}]}],
         "generationConfig":{"maxOutputTokens":18000,"temperature":0.3}},
        {"Content-Type":"application/json"})
    return _parse(r["candidates"][0]["content"]["parts"][0]["text"])

def _openai(key, path):
    r = _post("https://api.openai.com/v1/chat/completions",
        {"model":"gpt-4o","max_tokens":18000,"messages":[{"role":"user","content":[
            {"type":"image_url","image_url":{"url":f"data:{_mime(path)};base64,{_b64(path)}","detail":"high"}},
            {"type":"text","text":PROMPT}]}]},
        {"Content-Type":"application/json","Authorization":f"Bearer {key}"})
    return _parse(r["choices"][0]["message"]["content"])

def _anthropic(key, path):
    r = _post("https://api.anthropic.com/v1/messages",
        {"model":"claude-haiku-4-5-20251001","max_tokens":18000,"messages":[{"role":"user","content":[
            {"type":"image","source":{"type":"base64","media_type":_mime(path),"data":_b64(path)}},
            {"type":"text","text":PROMPT}]}]},
        {"Content-Type":"application/json","x-api-key":key,"anthropic-version":"2023-06-01"})
    return _parse(r["content"][0]["text"])

PROVIDERS = {"gemini":_gemini,"openai":_openai,"anthropic":_anthropic}

def analyze_image(image_path: str, retries: int = 3) -> Dict[str, Any]:
    key, provider = _get_provider()
    if not key: return {"error":"no_api_key"}
    if not os.path.exists(image_path): return {"error":"file_not_found"}
    fn = PROVIDERS.get(provider)
    if not fn: return {"error":"unknown_provider"}

    last_err = None
    for attempt in range(1, retries+1):
        try:
            result = fn(key, image_path)
            result["_provider"] = provider
            logger.info(f"✅ Tahlil qilindi ({provider}, {attempt}-urinish)")
            return result
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            logger.warning(f"HTTP {e.code} ({attempt}/{retries})")
            if e.code == 429:
                wait = 30 * attempt
                logger.info(f"Rate limit — {wait}s kutilmoqda...")
                time.sleep(wait)
                last_err = {"error": "rate_limit"}
                continue
            if e.code in (401, 403): 
                return {"error": "auth_error"}
            last_err = {"error": f"http_{e.code}"}
        except json.JSONDecodeError:
            last_err = {"error":"parse_error"}; logger.warning(f"JSON xato ({attempt}/{retries})")
        except Exception as e:
            last_err = {"error":str(e)}; logger.warning(f"Xato ({attempt}/{retries}): {e}")
        if attempt < retries: time.sleep(5)

    return last_err or {"error":"failed"}

def search_by_analysis(analysis: Dict) -> List:
    from database import db
    results, seen = [], set()
    def add(rows):
        for r in rows:
            if r["id"] not in seen: seen.add(r["id"]); results.append(r)
    cat      = (analysis.get("category") or "").lower().strip()
    keywords = analysis.get("name_keywords") or []
    color    = analysis.get("color") or ""
    fmt      = analysis.get("format") or ""
    thick    = analysis.get("thickness") or ""
    for kw in keywords:
        if len(kw.strip())>1:
            rows = db.search_by_name(kw.strip())
            if cat: rows=[r for r in rows if r["category"]==cat]
            add(rows)
    if color and len(color)>2:
        rows = db.search_by_name(color)
        if cat: rows=[r for r in rows if r["category"]==cat]
        add(rows)
    if fmt:   add(db.search_by_format(fmt.replace(" ","").replace("x","*").replace("х","*")))
    if thick: add(db.search_by_thickness(thick.replace(" ","")))
    if not results and cat: add(db.get_products_by_category(cat))
    return results

def build_detected_info(analysis: Dict) -> str:
    parts = []
    if analysis.get("_provider"): parts.append(f"🤖 {analysis['_provider'].capitalize()}")
    if analysis.get("category"):  parts.append(f"📂 {analysis['category']}")
    if analysis.get("color"):     parts.append(f"🎨 {analysis['color']}")
    if analysis.get("format"):    parts.append(f"📐 {analysis['format']}")
    if analysis.get("thickness"): parts.append(f"📏 {analysis['thickness']}")
    kws = analysis.get("name_keywords",[])
    if kws: parts.append(f"🔑 {', '.join(kws[:3])}")
    return " | ".join(parts) if parts else "?"
