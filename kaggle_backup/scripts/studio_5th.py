#!/usr/bin/env python3
"""Probe-and-commit a 5th text image (greeting-card style) at 50 steps to
complete the set of 5 max-quality text-rendering images."""
import base64, io, json, re, time, urllib.request
import numpy as np
from PIL import Image, ImageOps
import pytesseract
API="http://127.0.0.1:7860"; DEST="/kaggle/working/Sito-per-intelligenti"
def get(p,t=30):
    with urllib.request.urlopen(API+p,timeout=t) as r: return json.loads(r.read().decode())
def post(p,pl,t=2400):
    rq=urllib.request.Request(API+p,data=json.dumps(pl).encode(),headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(rq,timeout=t) as r: return json.loads(r.read().decode())
def stats(b64):
    raw=base64.b64decode(re.sub(r"^data:image/[^;]+;base64,","",b64))
    a=np.asarray(Image.open(io.BytesIO(raw)).convert("L")).astype("float32")
    g=(np.abs(np.diff(a,axis=1)).mean()+np.abs(np.diff(a,axis=0)).mean())/2
    return float(a.std()),float(g),raw
def validate(b64):
    s,g,raw=stats(b64); im=Image.open(io.BytesIO(raw)).convert("L")
    txt=pytesseract.image_to_string(ImageOps.autocontrast(im)).strip()
    bl=("safety" in txt.lower() or "block" in txt.lower())
    return {"std":round(s,1),"detail":round(g,2),"ocr":txt[:40].replace("\n"," "),"blocked":bool(bl),"real":bool((not bl) and s>20 and g>3)},raw
for _ in range(120):
    try:
        d=get("/api/health",10)
        if d.get("ok") and not d.get("mock"): break
    except Exception: pass
    time.sleep(5)
# candidate greeting-card prompts (greeting-card style reliably survives the filter)
CANDS=[("06_text_with_love",{"description":"an elegant hand-lettered greeting card that reads 'WITH LOVE' in flowing gold calligraphy inside a delicate watercolour wreath of pink roses and eucalyptus","text":"WITH LOVE","subject":"card reading WITH LOVE","style":"soft watercolour with gold-foil lettering","setting":"cream textured paper","lighting":"soft studio light","colors":"blush pink, sage green, gold","mood":"warm, loving","details":"crisp gold calligraphy, roses, eucalyptus, tiny gold dots"}),
       ("06_text_well_done",{"description":"a cheerful watercolour greeting card that reads 'WELL DONE' with confetti, stars and a small trophy","text":"WELL DONE","subject":"card reading WELL DONE","style":"playful watercolour illustration","setting":"cream paper","lighting":"soft","colors":"gold, blue, coral","mood":"celebratory","details":"legible lettering, confetti, stars, trophy"})]
done=False
for name,pj in CANDS:
    if done: break
    prompt=json.dumps(pj,ensure_ascii=False)
    for seed in (11,33,7,21,42,99,123):
        try:
            pr=post("/api/generate",{"prompt":prompt,"count":1,"steps":8,"width":512,"height":512,"seed":seed})
            ps,pg,_=stats(pr["images"][0]); surv=ps>16 and pg>1.2
            print(f"[5th] {name} probe seed={seed} std={ps:.1f} grad={pg:.2f} survived={surv}",flush=True)
            if not surv: continue
            full=post("/api/generate",{"prompt":prompt,"count":1,"steps":50,"width":1024,"height":1024,"seed":seed})
            v,raw=validate(full["images"][0]);open(f"/kaggle/working/{name}.png","wb").write(raw);v["seed"]=seed
            print(f"[5th] {name} COMMIT seed={seed} -> {v}",flush=True)
            if v["real"]: open(f"{DEST}/{name}.png","wb").write(raw); done=True; break
        except Exception as e: print(f"[5th] {name} seed={seed} EXC {e}",flush=True)
print("FIFTH_DONE got=%s"%done,flush=True)
