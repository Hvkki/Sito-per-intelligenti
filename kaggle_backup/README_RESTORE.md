# Kaggle session backup — Мамина Студія

Snapshot of the working Kaggle session (Ideogram-4 studio on 2× T4), saved so a
new session can be restored. See `motorproject/.kiro/skills/mamina-studia/SKILL.md`
for the full runbook.

## Contents
- `motorproject/` — full project source **including the img2img fix**
  (`backend/ideogram_engine.py`) and the Kiro skill (`.kiro/skills/...`).
- `scripts/` — generation/img2img drivers, dependency installer, server launcher.
- `images/` — all generated PNGs (text2img, text-rendering showcase, img2img, and
  the blocked-vs-real safety-filter comparison set).
- `summaries/` — per-run validation JSON (std/detail/OCR/blocked) + torch pins.
- `logs/` — install + server + driver logs.

## NOT included (by design)
- `.studio_env` — the Hugging Face token (secret). Re-add your own.
- `.hf_cache/` — ~16 GB gated Ideogram-4 weights. Re-downloaded on first run.

## Restore in a new Kaggle session (2× T4, Internet on)
1. `git clone` this repo; the studio source is under `kaggle_backup/motorproject`
   (or clone `Hvkki/motorproject` @ `add-mamina-studia` for the canonical copy).
2. Add Kaggle secret `HF_TOKEN`; accept the licence on
   huggingface.co/ideogram-ai/ideogram-4-nf4.
3. Run `kaggle_backup/scripts/setup_studio.sh` then `run_server.sh`.
4. **Always prompt with rich structured JSON** (see SKILL.md §5) — plain prompts
   are blocked by the model's safety filter.
