#!/usr/bin/env python3
"""Post-fix driver:
  1. Verify the VRAM-fixed flow-matching img2img (2 strengths, before/after).
  2. Re-roll the text images that the safety filter blocked, now as SCENE-RICH
     prompts (text embedded in a detailed scene -> passes far more reliably),
     50 steps, up to 2 attempts each (fresh random seed) until a real image.
"""
import base64, io, json, re, time, urllib.request
import numpy as np
from PIL import Image, ImageOps
import pytesseract

API = "http://127.0.0.1:7860"; DEST = "/kaggle/working/Sito-per-intelligenti"

def get(p, t=30):
    with urllib.request.urlopen(API + p, timeout=t) as r: return json.loads(r.read().decode())
def post(p, payload, t=2400):
    req = urllib.request.Request(API + p, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=t) as r: return json.loads(r.read().decode())
def validate(b64):
    raw = base64.b64decode(re.sub(r"^data:image/[^;]+;base64,", "", b64))
    im = Image.open(io.BytesIO(raw)).convert("L"); a = np.asarray(im).astype("float32")
    g = (np.abs(np.diff(a, axis=1)).mean() + np.abs(np.diff(a, axis=0)).mean()) / 2
    txt = pytesseract.image_to_string(ImageOps.autocontrast(im)).strip()
    blocked = ("safety" in txt.lower() or "block" in txt.lower())
    return {"bytes": len(raw), "std": round(float(a.std()),1), "detail": round(float(g),2),
            "ocr": txt[:50].replace("\n"," "), "blocked": bool(blocked),
            "real": bool((not blocked) and a.std()>20 and g>3)}, raw

print("[fix] waiting for model ready...", flush=True)
ok = False
for _ in range(120):
    try:
        d = get("/api/health", 10)
        if d.get("ok") and not d.get("mock"): ok = True; print("[fix] ready", flush=True); break
    except Exception: pass
    time.sleep(5)
if not ok: print("[fix] not ready"); raise SystemExit(1)

summary = {}

# ---- 1) img2img (VRAM-fixed) ----
img = Image.open("/kaggle/working/02_mountain_lake.png").convert("RGB")
buf = io.BytesIO(); img.save(buf, format="PNG")
data_url = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
img.save(f"{DEST}/img2img_BEFORE_mountain_lake.png")
TRANSFORM = {"description":"the same mountain lake scene transformed into vivid autumn, fiery red orange and golden foliage on the forest, warm afternoon light, colourful leaves reflected in the calm water",
 "subject":"autumn alpine lake and snow-dusted peaks","style":"highly detailed landscape photography","setting":"alpine valley in peak fall colour",
 "lighting":"warm golden afternoon light","colors":"crimson, amber, gold, deep teal water","mood":"vivid, cosy, serene","details":"colourful fallen leaves, rich mirror reflections, gentle ripples"}
for s in (0.45, 0.70):
    name = f"img2img_autumn_s{int(s*100):02d}"; print(f"[fix] {name}...", flush=True); t=time.time()
    try:
        res = post("/api/img2img", {"image":data_url,"prompt":json.dumps(TRANSFORM,ensure_ascii=False),"strength":s,"count":1,"steps":40})
        if "error" in res: summary[name]={"error":res["error"][:140]}
        else:
            v,raw = validate(res["images"][0]); open(f"/kaggle/working/{name}.png","wb").write(raw)
            if v["real"]: open(f"{DEST}/{name}.png","wb").write(raw)
            v["elapsed"]=res.get("elapsed"); v["wall"]=round(time.time()-t,1); summary[name]=v
        print(f"[fix] {name} -> {summary[name]}", flush=True)
    except Exception as e: summary[name]={"error":str(e)[:140]}; print(f"[fix] {name} EXC {e}", flush=True)
    json.dump(summary, open("/kaggle/working/fix_summary.json","w"), indent=2, ensure_ascii=False)

# ---- 2) re-roll blocked text images as SCENE-RICH prompts ----
SCENE_TEXT = {
 "05_text_fresh_coffee": {"description":"a cosy rustic cafe interior at morning, a steaming cappuccino in a ceramic cup on a wooden table beside a small black chalkboard sign that clearly reads 'FRESH COFFEE', pastries and potted plants behind, warm light, bokeh",
   "subject":"cafe table with a 'FRESH COFFEE' chalkboard sign","style":"warm realistic photography, shallow depth of field","setting":"rustic coffee shop interior","lighting":"soft warm morning light","colors":"warm browns, cream, green","mood":"cosy, inviting","details":"legible chalk lettering, latte art, steam, wood grain"},
 "06_text_dream_big": {"description":"a cosy child's bedroom at night, a warm glowing neon sign on the wall that clearly reads 'DREAM BIG' above a neatly made bed, fairy lights, books and toys, a window with a starry sky",
   "subject":"bedroom wall neon sign reading 'DREAM BIG'","style":"cosy detailed interior photography","setting":"child's bedroom at night","lighting":"warm neon glow and fairy lights","colors":"deep blue, warm amber, soft pink","mood":"dreamy, comforting","details":"legible neon letters, plush toys, starry window, soft shadows"},
 "07_text_visit_alps": {"description":"a sunny alpine train platform, a vintage blue enamel travel sign that clearly reads 'VISIT THE ALPS', a little red train, travellers with luggage, snow-capped peaks and pine forest behind, crisp detail",
   "subject":"alpine station sign reading 'VISIT THE ALPS'","style":"highly detailed travel photography","setting":"mountain railway platform","lighting":"bright clear daylight","colors":"teal, white snow, warm red accents","mood":"adventurous, cheerful","details":"legible enamel lettering, vintage train, luggage, wildflowers"},
 "08_text_welcome_kitten": {"description":"a fluffy ginger kitten sitting on a sunlit wooden porch holding up a small hand-painted wooden sign that clearly reads 'WELCOME', potted daisies, a cottage door behind, warm golden hour, cute and cosy",
   "subject":"ginger kitten holding a 'WELCOME' sign","style":"adorable detailed 3D render, Pixar-like","setting":"cottage porch at golden hour","lighting":"warm golden hour light","colors":"warm orange, cream, soft green","mood":"friendly, heart-warming","details":"legible painted letters, fluffy fur, big eyes, potted flowers"},
}
for name, pj in SCENE_TEXT.items():
    got = False
    for attempt in (1, 2):
        print(f"[fix] {name} attempt {attempt} (50 steps)...", flush=True); t=time.time()
        try:
            res = post("/api/generate", {"prompt":json.dumps(pj,ensure_ascii=False),"count":1,"steps":50})
            v,raw = validate(res["images"][0]); open(f"/kaggle/working/{name}.png","wb").write(raw)
            v["elapsed"]=res.get("elapsed"); v["wall"]=round(time.time()-t,1); v["attempt"]=attempt
            summary[name]=v; print(f"[fix] {name} -> {v}", flush=True)
            if v["real"]:
                open(f"{DEST}/{name}.png","wb").write(raw); got=True; break
        except Exception as e:
            summary[name]={"error":str(e)[:140]}; print(f"[fix] {name} EXC {e}", flush=True)
        json.dump(summary, open("/kaggle/working/fix_summary.json","w"), indent=2, ensure_ascii=False)
    json.dump(summary, open("/kaggle/working/fix_summary.json","w"), indent=2, ensure_ascii=False)

print("FIX_DONE", flush=True)
