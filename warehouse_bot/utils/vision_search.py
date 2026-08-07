import os,json,base64,logging,time,urllib.request,urllib.error
from typing import Dict,List,Any,Optional,Tuple
logger=logging.getLogger(__name__)
PROMPT="""Bu omborxona mahsuloti rasmi. Faqat JSON qaytaring:
{"name_keywords":["2-5 kalit so'z"],"category":"akril/mdf/xdf/laminat/kromka/zapchastlar yoki null","format":"masalan 2800*2070 yoki null","thickness":"masalan 18mm yoki null","color":"rang o'zbekcha","description":"1 jumla o'zbekcha"}"""

def _get_provider():
    for env,prov in [("GEMINI_API_KEY","gemini"),("GOOGLE_API_KEY","gemini"),("OPENAI_API_KEY","openai"),("ANTHROPIC_API_KEY","anthropic")]:
        k=os.environ.get(env,"").strip()
        if k: return k,prov
    return None,None

def _b64(p):
    with open(p,"rb") as f: return base64.b64encode(f.read()).decode()

def _mime(p):
    e=os.path.splitext(p)[1].lower().strip(".")
    return {"jpg":"image/jpeg","jpeg":"image/jpeg","png":"image/png","webp":"image/webp"}.get(e,"image/jpeg")

def _post(url,payload,headers):
    d=json.dumps(payload).encode()
    req=urllib.request.Request(url,data=d,headers=headers,method="POST")
    with urllib.request.urlopen(req,timeout=45) as r: return json.loads(r.read().decode())

def _parse(raw):
    raw=raw.strip()
    if "```" in raw:
        for p in raw.split("```"):
            p=p.strip()
            if p.startswith("json"): p=p[4:].strip()
            if p.startswith("{"): raw=p; break
    return json.loads(raw)

def _gemini(key,path):
    r=_post(f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}",
        {"contents":[{"parts":[{"text":PROMPT},{"inline_data":{"mime_type":_mime(path),"data":_b64(path)}}]}],
         "generationConfig":{"maxOutputTokens":500,"temperature":0.1}},{"Content-Type":"application/json"})
    return _parse(r["candidates"][0]["content"]["parts"][0]["text"])

def _openai(key,path):
    r=_post("https://api.openai.com/v1/chat/completions",
        {"model":"gpt-4o-mini","max_tokens":500,"messages":[{"role":"user","content":[
            {"type":"image_url","image_url":{"url":f"data:{_mime(path)};base64,{_b64(path)}"}},
            {"type":"text","text":PROMPT}]}]},
        {"Content-Type":"application/json","Authorization":f"Bearer {key}"})
    return _parse(r["choices"][0]["message"]["content"])

def _anthropic(key,path):
    r=_post("https://api.anthropic.com/v1/messages",
        {"model":"claude-haiku-4-5-20251001","max_tokens":500,"messages":[{"role":"user","content":[
            {"type":"image","source":{"type":"base64","media_type":_mime(path),"data":_b64(path)}},
            {"type":"text","text":PROMPT}]}]},
        {"Content-Type":"application/json","x-api-key":key,"anthropic-version":"2023-06-01"})
    return _parse(r["content"][0]["text"])

PROVIDERS={"gemini":_gemini,"openai":_openai,"anthropic":_anthropic}

def analyze_image(image_path,retries=3):
    key,provider=_get_provider()
    if not key: return {"error":"no_api_key"}
    if not os.path.exists(image_path): return {"error":"file_not_found"}
    fn=PROVIDERS.get(provider)
    if not fn: return {"error":"unknown_provider"}
    last_err=None
    for attempt in range(1,retries+1):
        try:
            result=fn(key,image_path); result["_provider"]=provider; return result
        except urllib.error.HTTPError as e:
            body=e.read().decode("utf-8",errors="ignore")
            if e.code==429: time.sleep(15*attempt); last_err={"error":"rate_limit"}; continue
            if e.code in(401,403): return {"error":"auth_error"}
            last_err={"error":f"http_{e.code}"}
        except json.JSONDecodeError: last_err={"error":"parse_error"}
        except Exception as e: last_err={"error":str(e)}
        if attempt<retries: time.sleep(5)
    return last_err or {"error":"failed"}

def search_by_analysis(analysis):
    from database import db
    results,seen=[],set()
    def add(rows):
        for r in rows:
            if r["id"] not in seen: seen.add(r["id"]); results.append(r)
    cat=(analysis.get("category") or "").lower().strip()
    for kw in(analysis.get("name_keywords") or []):
        if len(kw.strip())>1:
            rows=db.search_by_name(kw.strip())
            if cat: rows=[r for r in rows if r["category"]==cat]
            add(rows)
    color=analysis.get("color") or ""
    if color and len(color)>2:
        rows=db.search_by_name(color)
        if cat: rows=[r for r in rows if r["category"]==cat]
        add(rows)
    fmt=analysis.get("format") or ""
    if fmt: add(db.search_by_format(fmt.replace(" ","").replace("x","*")))
    thick=analysis.get("thickness") or ""
    if thick: add(db.search_by_thickness(thick.replace(" ","")))
    if not results and cat: add(db.get_products_by_category(cat))
    return results

def build_detected_info(analysis):
    parts=[]
    if analysis.get("_provider"): parts.append(f"🤖 {analysis['_provider'].capitalize()}")
    if analysis.get("category"):  parts.append(f"📂 {analysis['category']}")
    if analysis.get("color"):     parts.append(f"🎨 {analysis['color']}")
    if analysis.get("format"):    parts.append(f"📐 {analysis['format']}")
    if analysis.get("thickness"): parts.append(f"📏 {analysis['thickness']}")
    kws=analysis.get("name_keywords",[])
    if kws: parts.append(f"🔑 {', '.join(kws[:3])}")
    return " | ".join(parts) if parts else "?"
