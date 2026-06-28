#!/usr/bin/env python3
"""Verify the VRAM-fixed img2img (uncond parked during encode), and probe-commit
one more text image (a greeting-card style that passes reliably) to reach 5."""
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
print("[f2] waiting ready...",flush=True)
ok=False
for _ in range(120):
    try:
        d=get("/api/health",10)
        if d.get("ok") and not d.get("mock"): ok=True;print("[f2] ready",flush=True);break
    except Exception: pass
    time.sleep(5)
if not ok: raise SystemExit(1)
summary={}

# 1) img2img verify (uncond-parked fix)
img=Image.open("/kaggle/working/02_mountain_lake.png").convert("RGB");buf=io.BytesIO();img.save(buf,"PNG")
durl="data:image/png;base64,"+base64.b64encode(buf.getvalue()).decode();img.save(f"{DEST}/img2img_BEFORE_mountain_lake.png")
TF={"description":"the same mountain lake transformed into vivid autumn, fiery red orange and golden foliage on the forest, warm afternoon light, colourful leaves reflected in the water","subject":"autumn alpine lake","style":"detailed landscape photography","setting":"alpine valley in fall","lighting":"warm afternoon light","colors":"crimson, amber, gold, teal","mood":"vivid, serene","details":"fallen leaves, reflections, ripples"}
for s in (0.45,0.70):
    name=f"img2img_autumn_s{int(s*100):02d}";print(f"[f2] {name}...",flush=True);t=time.time()
    try:
        res=post("/api/img2img",{"image":durl,"prompt":json.dumps(TF,ensure_ascii=False),"strength":s,"count":1,"steps":40})
        if "error" in res: summary[name]={"error":res["error"][:120]}
        else:
            v,raw=validate(res["images"][0]);open(f"/kaggle/working/{name}.png","wb").write(raw)
            if v["real"]: open(f"{DEST}/{name}.png","wb").write(raw)
            v["wall"]=round(time.time()-t,1);summary[name]=v
        print(f"[f2] {name} -> {summary[name]}",flush=True)
    except Exception as e: summary[name]={"error":str(e)[:120]};print(f"[f2] {name} EXC {e}",flush=True)
    json.dump(summary,open("/kaggle/working/f2_summary.json","w"),indent=2,ensure_ascii=False)

# 2) 5th text image (greeting-card style passes reliably) via probe-commit
pj={"description":"an elegant hand-lettered greeting card that reads 'BEST WISHES' in flowing gold calligraphy, surrounded by a delicate watercolour wreath of roses and eucalyptus","text":"BEST WISHES","subject":"greeting card reading BEST WISHES","style":"soft watercolour with gold-foil lettering","setting":"cream textured paper","lighting":"soft studio light","colors":"blush pink, sage green, gold","mood":"warm, celebratory","details":"crisp gold calligraphy, roses, eucalyptus, tiny gold dots"}
prompt=json.dumps(pj,ensure_ascii=False); name="06_text_best_wishes"; got=False
for seed in (11,33,7,21,42,99):
    try:
        pr=post("/api/generate",{"prompt":prompt,"count":1,"steps":8,"width":512,"height":512,"seed":seed})
        ps,pg,_=stats(pr["images"][0]); surv=ps>16 and pg>1.2
        print(f"[f2] {name} probe seed={seed} std={ps:.1f} grad={pg:.2f} survived={surv}",flush=True)
        if not surv: continue
        full=post("/api/generate",{"prompt":prompt,"count":1,"steps":50,"width":1024,"height":1024,"seed":seed})
        v,raw=validate(full["images"][0]);open(f"/kaggle/working/{name}.png","wb").write(raw);v["seed"]=seed
        print(f"[f2] {name} COMMIT seed={seed} -> {v}",flush=True)
        if v["real"]: open(f"{DEST}/{name}.png","wb").write(raw);got=True;summary[name]=v;break
    except Exception as e: print(f"[f2] {name} seed={seed} EXC {e}",flush=True)
summary.setdefault(name,{"got":got})
json.dump(summary,open("/kaggle/working/f2_summary.json","w"),indent=2,ensure_ascii=False)
print("F2_DONE",flush=True)
