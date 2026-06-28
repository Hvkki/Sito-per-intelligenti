#!/usr/bin/env bash
# Back up the meaningful /kaggle/working artifacts into the Sito-per-intelligenti
# repo so a new Kaggle session can restore them.
# EXCLUDES (critical): .studio_env (HF token secret) and .hf_cache (~16GB gated
# model weights — too big for git + non-redistributable).
set -uo pipefail
SRC=/kaggle/working
REPO=/kaggle/working/Sito-per-intelligenti
DEST="$REPO/kaggle_backup"
echo "=== backing up to $DEST ==="
rm -rf "$DEST"
mkdir -p "$DEST/scripts" "$DEST/logs" "$DEST/summaries" "$DEST/images"

# scripts
cp -f "$SRC"/studio_*.py "$SRC"/setup_studio.sh "$SRC"/run_server.sh "$SRC"/backup_to_sito.sh "$DEST/scripts/" 2>/dev/null || true
# logs (verified token-free)
cp -f "$SRC"/*.log "$DEST/logs/" 2>/dev/null || true
# summaries + pins
cp -f "$SRC"/*_summary.json "$SRC"/torch-constraints.txt "$DEST/summaries/" 2>/dev/null || true
# all generated images
cp -f "$SRC"/*.png "$DEST/images/" 2>/dev/null || true

# full motorproject source snapshot WITH the img2img fix + Kiro skill,
# excluding git internals, byte-code, and any stray weights cache.
rsync -a --delete \
  --exclude '.git' --exclude '__pycache__' --exclude '*.pyc' \
  --exclude '.hf_cache' --exclude 'outputs' \
  "$SRC/motorproject/" "$DEST/motorproject/"

# SAFETY: make sure no HF token slipped into the backup
# SAFETY: make sure no full HF token slipped into the backup (regex matches the
# real 30+ char token, NOT this script's short check-string).
if grep -rIEl "hf_[A-Za-z0-9]{26,}" "$DEST" >/dev/null 2>&1; then
  echo "!! TOKEN FOUND IN BACKUP — aborting"; grep -rIEl "hf_[A-Za-z0-9]{26,}" "$DEST"; exit 1
fi
# SAFETY: ensure the secret + weights are NOT present
[ -e "$DEST/.studio_env" ] && { echo "!! .studio_env present — removing"; rm -f "$DEST/.studio_env"; }
find "$DEST" -name '.studio_env' -delete 2>/dev/null || true

cat > "$DEST/README_RESTORE.md" <<'MD'
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
MD

echo "=== backup tree (top) ==="; ls -la "$DEST"; echo "--- sizes ---"; du -sh "$DEST"/* 2>/dev/null
echo "BACKUP_DONE"
