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
