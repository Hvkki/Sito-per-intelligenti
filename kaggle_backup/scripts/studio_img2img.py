#!/usr/bin/env python3
"""Wait for the model to be ready, then exercise the NEW flow-matching img2img:
transform a previously generated base image with a rich-JSON prompt at two
strengths, validate each output is a real (unblocked) image, and copy results
into Sito-per-intelligenti as before/after pairs."""
import base64, io, json, re, time, urllib.request
import numpy as np
from PIL import Image, ImageOps
import pytesseract

API = "http://127.0.0.1:7860"
DEST = "/kaggle/working/Sito-per-intelligenti"
BASE_PNG = "/kaggle/working/02_mountain_lake.png"   # generated earlier

def get(path, timeout=30):
    with urllib.request.urlopen(API + path, timeout=timeout) as r:
        return json.loads(r.read().decode())

def post(path, payload, timeout=1200):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(API + path, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

def validate(b64):
    b = re.sub(r"^data:image/[^;]+;base64,", "", b64)
    raw = base64.b64decode(b)
    im = Image.open(io.BytesIO(raw)).convert("L")
    a = np.asarray(im).astype("float32")
    g = (np.abs(np.diff(a, axis=1)).mean() + np.abs(np.diff(a, axis=0)).mean()) / 2
    txt = pytesseract.image_to_string(ImageOps.autocontrast(im)).strip()
    blocked = ("safety" in txt.lower() or "block" in txt.lower())
    real = (not blocked) and a.std() > 20 and g > 3
    return {"bytes": len(raw), "std": round(float(a.std()), 1), "detail": round(float(g), 2),
            "ocr": txt[:40], "blocked": bool(blocked), "real": bool(real)}, raw

# 1. wait for the model to finish (re)loading in real GPU mode
print("[img2img] waiting for model ready...", flush=True)
ready = False
for _ in range(90):
    try:
        d = get("/api/health", timeout=10)
        if d.get("ok") and not d.get("mock"):
            print(f"[img2img] ready: {d.get('device',{}).get('mode')}", flush=True)
            ready = True
            break
    except Exception:
        pass
    time.sleep(5)
if not ready:
    print("[img2img] model not ready; aborting", flush=True); raise SystemExit(1)

# 2. build the init-image data URL
img = Image.open(BASE_PNG).convert("RGB")
buf = io.BytesIO(); img.save(buf, format="PNG")
data_url = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
print(f"[img2img] base {BASE_PNG} {img.size}", flush=True)

TRANSFORM = {
    "description": "the same serene mountain lake scene transformed into vivid autumn, fiery red orange and "
                   "golden foliage covering the forest, warm afternoon light, colourful leaves reflected in the calm water",
    "subject": "autumn alpine lake and snow-dusted peaks",
    "style": "highly detailed landscape photography, ultra sharp",
    "setting": "alpine valley in peak fall colour",
    "lighting": "warm golden afternoon light",
    "colors": "crimson, amber, gold, deep teal water",
    "mood": "vivid, cosy, serene",
    "details": "colourful fallen leaves, rich mirror reflections, gentle ripples",
}

summary = {}
for strength in (0.45, 0.70):
    name = f"img2img_autumn_s{int(strength*100):02d}"
    print(f"[img2img] {name} strength={strength} starting...", flush=True)
    t = time.time()
    try:
        res = post("/api/img2img", {"image": data_url,
                                    "prompt": json.dumps(TRANSFORM, ensure_ascii=False),
                                    "strength": strength, "count": 1})
        if "error" in res:
            summary[name] = {"error": res["error"]}
            print(f"[img2img] {name} ERROR {res['error']}", flush=True)
        else:
            v, raw = validate(res["images"][0])
            open(f"/kaggle/working/{name}.png", "wb").write(raw)
            if v["real"]:
                open(f"{DEST}/{name}.png", "wb").write(raw)
            v["server_elapsed"] = res.get("elapsed"); v["mock"] = res.get("mock"); v["wall"] = round(time.time() - t, 1)
            summary[name] = v
            print(f"[img2img] {name} -> {v}", flush=True)
    except Exception as e:
        summary[name] = {"error": str(e)}
        print(f"[img2img] {name} EXC {e}", flush=True)
    json.dump(summary, open("/kaggle/working/img2img_summary.json", "w"), indent=2, ensure_ascii=False)

# also copy the base alongside for a before/after comparison
Image.open(BASE_PNG).convert("RGB").save(f"{DEST}/img2img_BEFORE_mountain_lake.png")
print("IMG2IMG_DONE", flush=True)
