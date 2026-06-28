#!/usr/bin/env bash
# Launch the Мамина Студія FastAPI backend across both T4 GPUs.
set -u
source /kaggle/working/.studio_env          # HF_TOKEN / HUGGING_FACE_HUB_TOKEN
export DUAL_GPU=1                            # spread model over 2 GPUs
export CFG_PARALLEL=1                        # uncond -> cuda:0, cond -> cuda:1 (parallel)
export PORT=7860
export HOST=0.0.0.0
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True  # reclaim fragmented VRAM (pre-torch)
export MAX_SEQ_LEN=768                       # trim text tokens (notebook v2)
export CACHE_INTERVAL=1                       # max quality: NO step caching (user: max quality)
# Keep HF cache on the roomy /kaggle/working volume.
export HF_HOME=/kaggle/working/.hf_cache
mkdir -p "$HF_HOME"
cd /kaggle/working/motorproject/backend
echo "[run] starting uvicorn server:app on :$PORT (DUAL_GPU=$DUAL_GPU CFG_PARALLEL=$CFG_PARALLEL) $(date -u +%H:%M:%S)"
exec python3 -m uvicorn server:app --host 0.0.0.0 --port 7860 --log-level info
