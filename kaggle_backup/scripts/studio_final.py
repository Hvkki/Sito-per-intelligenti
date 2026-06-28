#!/usr/bin/env python3
"""Final showcase driver:
  1. validate the VRAM-fixed flow-matching img2img (2 strengths) on a base image
  2. generate 5 MAX-QUALITY images (50 steps, no step-caching) that each render
     legible TEXT (Ideogram-4's signature strength), per the user's request.
All outputs validated (real / not safety-blocked) and copied to Sito-per-intelligenti."""
import base64, io, json, re, time, urllib.request
import numpy as np
from PIL import Image, ImageOps
import pytesseract

API = "http://127.0.0.1:7860"
DEST = "/kaggle/working/Sito-per-intelligenti"

def get(path, timeout=30):
    with urllib.request.urlopen(API + path, timeout=timeout) as r:
        return json.loads(r.read().decode())

def post(path, payload, timeout=2400):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(API + path, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

def validate(b64):
    raw = base64.b64decode(re.sub(r"^data:image/[^;]+;base64,", "", b64))
    im = Image.open(io.BytesIO(raw)).convert("L")
    a = np.asarray(im).astype("float32")
    g = (np.abs(np.diff(a, axis=1)).mean() + np.abs(np.diff(a, axis=0)).mean()) / 2
    txt = pytesseract.image_to_string(ImageOps.autocontrast(im)).strip()
    blocked = ("safety" in txt.lower() or "block" in txt.lower())
    real = (not blocked) and a.std() > 20 and g > 3
    return {"bytes": len(raw), "std": round(float(a.std()), 1), "detail": round(float(g), 2),
            "ocr": txt[:60].replace("\n", " "), "blocked": bool(blocked), "real": bool(real)}, raw

print("[final] waiting for model ready...", flush=True)
ready = False
for _ in range(120):
    try:
        d = get("/api/health", timeout=10)
        if d.get("ok") and not d.get("mock"):
            print(f"[final] ready: {d['device']['mode']} steps_default={d['defaults']['steps']}", flush=True)
            ready = True; break
    except Exception:
        pass
    time.sleep(5)
if not ready:
    print("[final] NOT READY; abort", flush=True); raise SystemExit(1)

summary = {}

# ---------- 1. img2img validation (VRAM-fixed) ----------
img = Image.open("/kaggle/working/02_mountain_lake.png").convert("RGB")
buf = io.BytesIO(); img.save(buf, format="PNG")
data_url = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
TRANSFORM = {
    "description": "the same mountain lake scene transformed into vivid autumn, fiery red orange and golden foliage, warm afternoon light, colourful leaves reflected in the calm water",
    "subject": "autumn alpine lake and snow-dusted peaks", "style": "highly detailed landscape photography",
    "setting": "alpine valley in peak fall colour", "lighting": "warm golden afternoon light",
    "colors": "crimson, amber, gold, deep teal water", "mood": "vivid, cosy, serene",
    "details": "colourful fallen leaves, rich mirror reflections, gentle ripples",
}
for strength in (0.45, 0.70):
    name = f"img2img_autumn_s{int(strength*100):02d}"
    print(f"[final] {name} starting...", flush=True); t = time.time()
    try:
        res = post("/api/img2img", {"image": data_url, "prompt": json.dumps(TRANSFORM, ensure_ascii=False),
                                    "strength": strength, "count": 1, "steps": 40})
        if "error" in res:
            summary[name] = {"error": res["error"][:160]}
        else:
            v, raw = validate(res["images"][0]); open(f"/kaggle/working/{name}.png", "wb").write(raw)
            if v["real"]:
                open(f"{DEST}/{name}.png", "wb").write(raw)
            v["elapsed"] = res.get("elapsed"); v["wall"] = round(time.time() - t, 1); summary[name] = v
        print(f"[final] {name} -> {summary[name]}", flush=True)
    except Exception as e:
        summary[name] = {"error": str(e)[:160]}; print(f"[final] {name} EXC {e}", flush=True)
    json.dump(summary, open("/kaggle/working/final_summary.json", "w"), indent=2, ensure_ascii=False)
img.save(f"{DEST}/img2img_BEFORE_mountain_lake.png")

# ---------- 2. five MAX-QUALITY text-rendering images (50 steps) ----------
TEXT_PROMPTS = {
    "04_text_happy_birthday": {
        "description": "a charming hand-lettered greeting card that reads 'Happy Birthday!' in elegant calligraphy, surrounded by watercolour flowers and gold confetti",
        "text": "Happy Birthday!", "subject": "greeting card with the words 'Happy Birthday!'",
        "style": "soft watercolour illustration with gold-foil accents", "setting": "cream textured paper",
        "lighting": "soft even studio light", "colors": "pastel pink, mint, gold", "mood": "joyful, warm",
        "details": "crisp legible lettering, delicate floral wreath, tiny hearts"},
    "05_text_fresh_coffee": {
        "description": "a cosy vintage cafe poster with bold text 'FRESH COFFEE' above a steaming cup of coffee",
        "text": "FRESH COFFEE", "subject": "retro coffee advertisement poster",
        "style": "vintage screen-print poster, clean typography", "setting": "warm beige background",
        "lighting": "flat poster lighting", "colors": "warm browns, cream, deep red", "mood": "inviting, nostalgic",
        "details": "bold legible sans-serif letters, steam swirls, coffee-bean border"},
    "06_text_dream_big": {
        "description": "an inspirational poster with large clean text 'DREAM BIG' over a starry mountain night sky",
        "text": "DREAM BIG", "subject": "motivational typographic poster",
        "style": "modern minimalist poster", "setting": "night sky full of stars over mountains",
        "lighting": "soft moonlight glow", "colors": "deep navy, white, soft gold stars", "mood": "uplifting, calm",
        "details": "crisp bold uppercase lettering, milky way, silhouetted peaks"},
    "07_text_visit_alps": {
        "description": "a vintage travel poster reading 'VISIT THE ALPS' with snow peaks and a little red train",
        "text": "VISIT THE ALPS", "subject": "retro travel poster",
        "style": "mid-century travel poster, flat illustration", "setting": "alpine valley with a railway",
        "lighting": "bright clear daylight", "colors": "teal sky, white snow, warm red accents", "mood": "adventurous, cheerful",
        "details": "clean readable display typography, pine trees, vintage train"},
    "08_text_welcome_kitten": {
        "description": "a cute ginger kitten holding up a small wooden sign that clearly reads 'WELCOME', cosy and warm",
        "text": "WELCOME", "subject": "ginger kitten holding a 'WELCOME' sign",
        "style": "adorable 3D render, Pixar-like", "setting": "sunlit wooden porch",
        "lighting": "warm golden hour", "colors": "warm orange, cream, soft green", "mood": "friendly, heart-warming",
        "details": "legible hand-painted letters on the sign, fluffy fur, big expressive eyes"},
}
for name, pj in TEXT_PROMPTS.items():
    print(f"[final] {name} (50 steps) starting...", flush=True); t = time.time()
    try:
        res = post("/api/generate", {"prompt": json.dumps(pj, ensure_ascii=False), "count": 1, "steps": 50})
        v, raw = validate(res["images"][0]); open(f"/kaggle/working/{name}.png", "wb").write(raw)
        if v["real"]:
            open(f"{DEST}/{name}.png", "wb").write(raw)
        v["elapsed"] = res.get("elapsed"); v["wall"] = round(time.time() - t, 1); summary[name] = v
        print(f"[final] {name} -> {v}", flush=True)
    except Exception as e:
        summary[name] = {"error": str(e)[:160]}; print(f"[final] {name} EXC {e}", flush=True)
    json.dump(summary, open("/kaggle/working/final_summary.json", "w"), indent=2, ensure_ascii=False)

print("FINAL_DONE", flush=True)
