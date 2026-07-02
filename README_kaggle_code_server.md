# Remote VS Code on Kaggle (code-server + ngrok)

A small, self-contained replacement for the old, unmaintained
[ColabCode](https://github.com/abhishekkrthakur/colabcode). It runs
[`code-server`](https://github.com/coder/code-server) (VS Code in the browser) on a
Kaggle kernel and exposes it through an **ngrok** tunnel using ngrok's current API.

## Why not just use ColabCode?

ColabCode is ~5 years old and breaks on today's ngrok:

- It calls `ngrok.connect(addr=port, options={"bind_tls": True})`, but modern
  `pyngrok`/ngrok rejects the `options` argument (`HTTP 400: invalid tunnel configuration`).
- ngrok now **requires an authenticated account/token** for every tunnel
  (`ERR_NGROK_4018`).
- It tries to pre-install extensions from `extensions.coder.com`, a domain that no
  longer exists (harmless `ENOTFOUND` errors).

This notebook does the same three jobs ColabCode did — install code-server, open a
tunnel, launch the editor — but with the current API and no dead extension calls.

## How to use

1. Open `kaggle_code_server.ipynb` in Kaggle (File -> Import Notebook, or import this
   repo).
2. **Enable Internet**: right sidebar -> Settings -> toggle Internet on.
3. **Add your ngrok token as a Secret** (never hardcode it):
   - Get a token: https://dashboard.ngrok.com/get-started/your-authtoken
   - Right sidebar -> Add-ons -> Secrets -> add a secret named `NGROK_TOKEN` and
     attach it to the notebook.
4. Run the cells in order.
5. Open the printed `https://...ngrok-free.app` URL. **No login is required** — the
   notebook launches code-server with `--auth none`.

## Security warning

This notebook runs code-server with **no password** (`--auth none`). Anyone who has the
ngrok URL gets full access to the Kaggle session (terminal, files, data), and ngrok URLs
can be discovered. Use it only for short, throwaway sessions, don't share the link, and
stop the kernel when done. To require a password instead, uncomment the password block at
the bottom of the launch cell.

## Notes

- ngrok's free tier allows one active tunnel; the launcher runs `ngrok.kill()` to clear
  stale sessions first.
- Kaggle kernels are temporary — when the session stops, the tunnel and editor stop too.
- The token is read at runtime from Kaggle Secrets, so it is never committed to Git.


## Persistence: making your work survive between sessions

Kaggle is not like rebooting your own computer. When a session ends, it wipes almost
everything. Only `/kaggle/working/` is kept, and only when you click **Save Version**
(commit). Installed tools (`code-server`, `kiro-cli`, `ngrok`) and your home directory
are wiped every session.

So there are two things to handle:

1. **Your files / progress** — the reliable option is Git. Work inside a clone under
   `/kaggle/working` and `git push` to GitHub to save:
   ```bash
   cd /kaggle/working
   git clone https://github.com/Hvkki/Sito-per-intelligenti.git
   cd Sito-per-intelligenti
   # ...work...
   git add -A && git commit -m "wip" && git push
   ```
   (Alternatively, keep files in `/kaggle/working` and use Kaggle's **Save Version** to
   snapshot them, but Git is more robust and portable.)

2. **The tools** — reinstall them each session with one command. Run this from a
   notebook cell at session start:
   ```bash
   !curl -fsSL https://raw.githubusercontent.com/Hvkki/Sito-per-intelligenti/main/bootstrap.sh | bash
   ```
   `bootstrap.sh` installs code-server + kiro-cli + pyngrok, starts code-server and an
   ngrok tunnel, and prints the URL. Then open the URL and use the VS Code terminal for
   everything else.

### Kiro CLI login on Kaggle (headless)

The normal browser login fails on Kaggle because it redirects to `localhost:3128` on the
remote kernel. Use the device flow instead, which gives you a code to enter on your own
machine:

```bash
kiro-cli login --license pro \
  --identity-provider https://d-906673ba2c.awsapps.com/start \
  --region us-east-1 \
  --use-device-flow
```

(For Builder ID / social login instead of an organization: `kiro-cli login --license free --use-device-flow`.)

Note: the Kiro CLI login is also wiped each session, so you re-run this once per session.
