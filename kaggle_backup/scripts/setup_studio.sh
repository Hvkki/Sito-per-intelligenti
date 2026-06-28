#!/usr/bin/env bash
# Mirrors MaminaStudia_Kaggle.ipynb dependency steps, with torch pinned so the
# pre-installed CUDA stack (and code-server env) is never upgraded/broken.
set -uo pipefail
echo "=== [setup] start $(date -u +%H:%M:%S) ==="

python3 -m pip -q install --upgrade pip

# Pin the exact torch stack already installed so nothing upgrades it.
CONSTRAINTS=/kaggle/working/torch-constraints.txt
python3 - <<'PY' > "$CONSTRAINTS"
import importlib
for m in ("torch","torchvision","torchaudio"):
    try:
        print(m+"=="+importlib.import_module(m).__version__)
    except Exception:
        pass
PY
echo "[setup] torch constraints:"; cat "$CONSTRAINTS"
C="-c $CONSTRAINTS"

set -e
echo "=== [setup] web stack ==="
python3 -m pip -q install $C fastapi 'uvicorn[standard]' pydantic python-multipart pillow pyngrok requests

echo "=== [setup] diffusers PR build (Ideogram4Pipeline) ==="
python3 -m pip -q install $C 'git+https://github.com/huggingface/diffusers.git@04b197eece42bfc88d1814b20e07987d94cccaa7'

echo "=== [setup] transformers/peft/accelerate/outlines ==="
python3 -m pip -q install $C transformers==5.8.0 peft==0.19.1 accelerate==1.10.1 outlines==1.3.0 sentencepiece safetensors

echo "=== [setup] bitsandbytes + nvjitlink ==="
python3 -m pip -q install $C 'bitsandbytes>=0.46.1'
python3 -m pip -q install $C nvidia-nvjitlink-cu13 || echo "nvjitlink-cu13 optional"
set +e

echo "=== [setup] import check ==="
python3 - <<'PY'
for m in ("torch","torchvision","transformers","diffusers","bitsandbytes","accelerate"):
    try:
        mod=__import__(m); print(f"  OK {m} {getattr(mod,'__version__','')}")
    except Exception as e:
        print(f"  WARN {m}: {type(e).__name__}: {e}")
try:
    from diffusers import Ideogram4Pipeline  # noqa
    print("  OK Ideogram4Pipeline available")
except Exception as e:
    print(f"  WARN Ideogram4Pipeline: {e}")
PY
echo "=== [setup] DONE $(date -u +%H:%M:%S) ==="
