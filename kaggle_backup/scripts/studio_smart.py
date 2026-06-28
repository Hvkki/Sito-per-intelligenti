#!/usr/bin/env python3
"""Smart driver:
  1. Verify the instrumented flow-matching img2img (512, logs cuda:0 memory).
  2. Generate text images via PROBE-AND-COMMIT (user's idea): a cheap low-step /
     low-res probe finds a seed that survives the safety filter, then we commit
     to a full 50-step / 1024 render at the SAME seed. Avoids paying full compute
     for seeds the filter rejects."""
import base64, io, json, re, time, urllib.request
import numpy as np
from PIL import Image, ImageOps
import pytesseract

API = "http://127.0.0.1:7860"; DEST = "/kaggle/working/Sito-per-intelligenti"
def get(p, t=30):
    with urllib.request.urlopen(API + p, timeout=t) as r: return json.loads(r.read().decode())
def post(p, payload, t=2400):
    req = urllib.request.Request(API + p, data=json.dumps(payload).encode(), headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=t) as r: return json.loads(r.read().decode())
def stats(b64):
    raw = base64.b64decode(re.sub(r"^data:image/[^;]+;base64,", "", b64))
    im = Image.open(io.BytesIO(raw)).convert("L"); a = np.asarray(im).astype("float32")
    g = (np.abs(np.diff(a,axis=1)).mean()+np.abs(np.diff(a,axis=0)).mean())/2
    return float(a.std()), float(g), raw
def validate(b64):
    s, g, raw = stats(b64)
    im = Image.open(io.BytesIO(raw)).convert("L")
    txt = pytesseract.image_to_string(ImageOps.autocontrast(im)).strip()
    blocked = ("safety" in txt.lower() or "block" in txt.lower())
    return {"std": round(s,1), "detail": round(g,2), "ocr": txt[:40].replace("\n"," "),
            "blocked": bool(blocked), "real": bool((not blocked) and s>20 and g>3)}, raw

print("[smart] waiting ready...", flush=True)
ok=False
for _ in range(120):
    try:
        d=get("/api/health",10)
        if d.get("ok") and not d.get("mock"): ok=True; print("[smart] ready", flush=True); break
    except Exception: pass
    time.sleep(5)
if not ok: raise SystemExit(1)
summary={}

# 1) img2img verify (instrumented; 512)
img=Image.open("/kaggle/working/02_mountain_lake.png").convert("RGB"); buf=io.BytesIO(); img.save(buf,"PNG")
data_url="data:image/png;base64,"+base64.b64encode(buf.getvalue()).decode(); img.save(f"{DEST}/img2img_BEFORE_mountain_lake.png")
TF={"description":"the same mountain lake transformed into vivid autumn, fiery red orange and golden foliage, warm light, leaves reflected in the water","subject":"autumn alpine lake","style":"detailed landscape photography","setting":"alpine valley in fall","lighting":"warm afternoon light","colors":"crimson, amber, gold, teal","mood":"vivid, serene","details":"fallen leaves, reflections, ripples"}
for s in (0.45,0.70):
    name=f"img2img_autumn_s{int(s*100):02d}"; print(f"[smart] {name}...",flush=True); t=time.time()
    try:
        res=post("/api/img2img",{"image":data_url,"prompt":json.dumps(TF,ensure_ascii=False),"strength":s,"count":1,"steps":40})
        if "error" in res: summary[name]={"error":res["error"][:120]}
        else:
            v,raw=validate(res["images"][0]); open(f"/kaggle/working/{name}.png","wb").write(raw)
            if v["real"]: open(f"{DEST}/{name}.png","wb").write(raw)
            v["wall"]=round(time.time()-t,1); summary[name]=v
        print(f"[smart] {name} -> {summary[name]}",flush=True)
    except Exception as e: summary[name]={"error":str(e)[:120]}; print(f"[smart] {name} EXC {e}",flush=True)
    json.dump(summary,open("/kaggle/working/smart_summary.json","w"),indent=2,ensure_ascii=False)

# 2) probe-and-commit text images
TEXT={
 "05_text_fresh_coffee":{"description":"a decorative cafe chalkboard sign that clearly reads 'FRESH COFFEE', framed by hand-drawn coffee cups and beans, warm cosy style","text":"FRESH COFFEE","subject":"chalkboard reading FRESH COFFEE","style":"hand-drawn chalk art","setting":"rustic cafe wall","lighting":"warm","colors":"cream chalk on dark slate, warm browns","mood":"cosy","details":"legible chalk lettering, swirls, beans"},
 "06_text_good_morning":{"description":"a cheerful watercolour card that reads 'GOOD MORNING' with a rising sun and birds and flowers","text":"GOOD MORNING","subject":"greeting card reading GOOD MORNING","style":"soft watercolour illustration","setting":"cream paper","lighting":"soft","colors":"warm yellow, peach, green","mood":"cheerful, gentle","details":"legible lettering, sun rays, little birds, flowers"},
 "07_text_thank_you":{"description":"an elegant hand-lettered card that reads 'THANK YOU' in gold calligraphy on a wreath of eucalyptus leaves","text":"THANK YOU","subject":"card reading THANK YOU","style":"elegant watercolour with gold foil","setting":"cream textured paper","lighting":"soft studio","colors":"sage green, gold, cream","mood":"warm, grateful","details":"crisp gold calligraphy, eucalyptus wreath"},
 "08_text_welcome_kitten":{"description":"a cute ginger kitten on a sunlit porch holding a small wooden sign that clearly reads 'WELCOME', potted daisies, cosy","text":"WELCOME","subject":"kitten holding a WELCOME sign","style":"adorable 3D render, Pixar-like","setting":"cottage porch, golden hour","lighting":"warm golden hour","colors":"orange, cream, green","mood":"friendly","details":"legible painted letters, fluffy fur, big eyes"},
}
for name,pj in TEXT.items():
    prompt=json.dumps(pj,ensure_ascii=False); rec={"probes":[]}; got=False
    for seed in (11,22,33,44,55,66):
        try:
            pr=post("/api/generate",{"prompt":prompt,"count":1,"steps":8,"width":512,"height":512,"seed":seed})
            ps,pg,_=stats(pr["images"][0]); survived = ps>16 and pg>1.2
            rec["probes"].append({"seed":seed,"std":round(ps,1),"grad":round(pg,2),"survived":bool(survived)})
            print(f"[smart] {name} probe seed={seed} std={ps:.1f} grad={pg:.2f} survived={survived}",flush=True)
            if not survived: continue
            full=post("/api/generate",{"prompt":prompt,"count":1,"steps":50,"width":1024,"height":1024,"seed":seed})
            v,raw=validate(full["images"][0]); open(f"/kaggle/working/{name}.png","wb").write(raw)
            v["seed"]=seed; rec.update(v)
            print(f"[smart] {name} COMMIT seed={seed} -> {v}",flush=True)
            if v["real"]:
                open(f"{DEST}/{name}.png","wb").write(raw); got=True; break
        except Exception as e:
            print(f"[smart] {name} seed={seed} EXC {e}",flush=True)
    rec["got"]=got; summary[name]=rec
    json.dump(summary,open("/kaggle/working/smart_summary.json","w"),indent=2,ensure_ascii=False)
print("SMART_DONE",flush=True)
