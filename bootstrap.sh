#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Kaggle session bootstrap: re-installs the tools that Kaggle wipes each session
# and (re)starts code-server + an ngrok tunnel.
#
# RUN THIS FROM A NOTEBOOK CELL at the start of a fresh Kaggle session:
#     !curl -fsSL https://raw.githubusercontent.com/Hvkki/Sito-per-intelligenti/main/bootstrap.sh | bash
#
# Once code-server is up, open the printed ngrok URL and do everything else
# (kiro-cli, git, etc.) from the VS Code terminal.
#
# Requirements:
#   - Notebook Internet enabled (Settings -> Internet).
#   - An ngrok token: either a Kaggle Secret named NGROK_TOKEN, or `export NGROK_TOKEN=...`.
# ---------------------------------------------------------------------------
set -euo pipefail

PORT="${PORT:-10000}"
export PATH="$HOME/.local/bin:$PATH"

echo "==> Ensuring tools are installed (Kaggle wipes these each session)..."
command -v code-server >/dev/null 2>&1 || curl -fsSL https://code-server.dev/install.sh | sh
command -v kiro-cli    >/dev/null 2>&1 || curl -fsSL https://cli.kiro.dev/install | bash
python3 -c "import pyngrok" >/dev/null 2>&1 || pip install -q pyngrok

# Locate (and auto-download if needed) the ngrok binary that pyngrok manages.
NGROK_BIN="$(python3 -c "from pyngrok import ngrok, conf; ngrok.install_ngrok(); print(conf.get_default().ngrok_path)")"

echo "==> Resolving ngrok token..."
if [ -z "${NGROK_TOKEN:-}" ]; then
  NGROK_TOKEN="$(python3 -c "from kaggle_secrets import UserSecretsClient; print(UserSecretsClient().get_secret('NGROK_TOKEN'))" 2>/dev/null || true)"
fi
if [ -z "${NGROK_TOKEN:-}" ]; then
  echo "ERROR: No ngrok token found." >&2
  echo "       Add a Kaggle Secret named NGROK_TOKEN, or run: export NGROK_TOKEN=your_token" >&2
  exit 1
fi
"$NGROK_BIN" config add-authtoken "$NGROK_TOKEN" >/dev/null

echo "==> Starting code-server (no auth) on port ${PORT}..."
pkill -f "code-server" 2>/dev/null || true
nohup code-server --bind-addr "0.0.0.0:${PORT}" --auth none >/tmp/code-server.log 2>&1 &

echo "==> Starting ngrok tunnel..."
pkill -f "ngrok" 2>/dev/null || true
nohup "$NGROK_BIN" http "${PORT}" --log=stdout >/tmp/ngrok.log 2>&1 &
sleep 6

URL="$(curl -s http://127.0.0.1:4040/api/tunnels \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['tunnels'][0]['public_url'])" 2>/dev/null || true)"

echo "============================================================"
echo " Code Server URL : ${URL:-<not ready - check: cat /tmp/ngrok.log>}"
echo " Auth            : NONE (anyone with this URL has full access)"
echo "============================================================"
echo
echo "Next, inside the VS Code terminal:"
echo "  1) Log in to Kiro CLI:"
echo "     kiro-cli login --license pro \\"
echo "       --identity-provider https://d-906673ba2c.awsapps.com/start \\"
echo "       --region us-east-1 --use-device-flow"
echo "  2) Work inside a git clone under /kaggle/working and 'git push' to save your progress."
