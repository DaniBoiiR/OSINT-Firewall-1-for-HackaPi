# Firewall 1 — Web Application Challenge
**Hack-A-PI** · corporate staff portal · Flask + Docker · air-gapped

A deliberately vulnerable corporate web portal for an offline, isolated CTF
lab. It presents as a polished, light-themed business intranet — **no hacker
aesthetic, no CTF flavor text, no hints in the app.** The intended web-layer
vulnerabilities are real; the container around them is hardened so those bugs
can't become host/network compromise on the shared lab LAN.

> **Organizer docs are intentionally separate and must stay off the player
> network:** `ORGANIZER_FLAGS.md` (flag + full solve), `NPC_BRIEFING_Aya_Nocari.md`
> (in-person hint ladder), `TECH_LEAD_HANDOFF.md` (deploy + network checklist).

---

## Quick start

```bash
docker compose up -d --build        # serves on host port 80
curl -s localhost/health            # -> ok
# open http://<host-ip>/ on the closed Wi-Fi
```

Rotate the flag without rebuilding:

```bash
cp .env.example .env                # edit FLAG=FLAG{...}
docker compose up -d
```

Run without Docker (dev):

```bash
python3 -m venv venv && . venv/bin/activate
pip install -r requirements.txt
gunicorn -c gunicorn.conf.py app:app   # or:  PORT=8080 python app.py
```

## What's inside

```
firewall-1-web/
├── app.py                  Flask app — all routes & in-memory data
├── gunicorn.conf.py        prod server tuning (Pi / ~40 users)
├── requirements.txt        Flask + gunicorn (only two deps)
├── Dockerfile              non-root, multi-arch (x86 + Pi arm64)
├── docker-compose.yml      one-command deploy, host :80, hardened
├── .env.example            flag rotation
├── templates/              Jinja templates (public site + portal)
├── static/
│   ├── css/app.css         pre-compiled Tailwind (bundled, no CDN)
│   ├── js/session.js       client session helper
│   └── img/favicon.svg
├── tailwind/ + package.json  OPTIONAL build-time CSS pipeline (not needed at runtime)
└── *.md                    organizer-only docs (see above)
```

## Design guarantees

- **Fully offline.** Zero external CDNs, fonts, or network calls. Tailwind is
  pre-compiled to `static/css/app.css`; fonts use the system stack. The only
  build-time network use is the initial `docker compose build`.
- **No persistence, no DB, no shell-out.** Challenge data lives in memory;
  requests can't read the filesystem or execute commands. Report IDs are
  integer-routed (no path traversal / LFI).
- **Hardened container.** Non-root user, `cap_drop: ALL`,
  `no-new-privileges`, read-only root filesystem + tmpfs.
- **Lightweight.** Two Python deps; `gunicorn` 4×4 threaded workers comfortably
  cover ~40 concurrent participants on a Pi 4/5.

## Rebuilding the stylesheet (optional)

The compiled CSS is committed, so you normally don't need Node. To regenerate
after editing templates:

```bash
npm install
npm run build:css        # writes static/css/app.css
```

## The challenge (one line, no spoilers)

Recon reveals an unlinked staff portal → the portal trusts a client-signed
session whose key was shipped to the browser → an admin-only incident viewer
fails to authorize per object. Full walkthrough: `ORGANIZER_FLAGS.md`.
