# Firewall 1 — Technical Lead Handoff & Deployment Checklist
### Web Application Challenge · Hack-A-PI · Friday pilot

**Lane boundary (unchanged):** organizers ship the *challenge software*; the
**technical lead** owns the Pi / laptop / router / CTFd. Red on *code* → back to
us. Red on *hardware / network / CTFd* → your lane.

**What this is:** one self-contained Flask app (a fictional corporate "staff
portal"), Dockerised, serving on **host port 80**. No database, no disk writes,
no root, air-gap-safe. Target host for the pilot: **Raspberry Pi** (arm64) — it
runs identically on the Command Center laptop if you'd rather colocate it.

---

## A. Pre-pull & build — WHILE INTERNET IS STILL UP  ⚠️ critical for air-gap
The container needs its base image and pip wheels **once**. Do this before the
network goes dark; after that it runs with zero internet.

- [ ] Docker + compose plugin installed on the host (`docker --version`, `docker compose version`).
- [ ] Copy the `firewall-1-web/` folder to the host.
- [ ] Build (pulls `python:3.12-slim` + Flask/gunicorn now): `docker compose build`
- [ ] Image present: `docker images | grep firewall-1-web`
- [ ] (Belt-and-braces) export a copy for re-flashing without internet:
      `docker save hackapi/firewall-1-web:1.0 -o firewall-1-web.tar`

## B. Stand-up & single-command deploy
- [ ] `docker compose up -d --build`
- [ ] Container healthy: `docker compose ps` shows **healthy** (give it ~15s).
- [ ] Loads locally: `curl -s localhost/health` → `ok`
- [ ] Loads in a browser on the host: `http://localhost/`  (clean corporate site, no errors).
- [ ] Decide persistence: `restart: unless-stopped` is already set → survives reboot. Confirm with a test reboot if time allows.

## C. Air-gap verification  ⚠️ the test that actually matters
- [ ] Disconnect the host from the internet (leave it on the closed lab LAN).
- [ ] `docker compose down && docker compose up -d` — **still starts, still serves.**
- [ ] `http://localhost/` renders fully: fonts, layout, blue/purple styling all load (everything is bundled — no CDN).

## D. Network reachability on the closed Wi-Fi — TECH + MUR/GDGoC
- [ ] Host LAN IP noted (e.g. `10.10.10.x`): ________________
- [ ] A second device on the closed Wi-Fi reaches `http://<host-ip>/`.
- [ ] Static DHCP lease pinned for the host (so the URL doesn't move mid-event).
- [ ] Optional friendly hostname (e.g. `portal.local` / router DNS entry): ________________
- [ ] **No port clash:** nothing else on the host is already on **:80** (CTFd, Ollama, other firewalls). `sudo ss -lptn 'sport = :80'` is empty before `up`.

## E. Flag & scoring — MUR/GDGoC
- [ ] Rotate the flag from default: `cp .env.example .env`, edit `FLAG=FLAG{...}`, then `docker compose up -d`. (No rebuild. Flag lives only in incident report #4663.)
- [ ] Loaded the rotated flag into **CTFd** with its point value; linked the challenge to `http://<host-ip>/`.
- [ ] Test-submitted the flag in CTFd → accepted.
- [ ] `ORGANIZER_FLAGS.md` kept **off** the player network and out of the Go-Bag.

## F. Full solve dry-run — MUR/GDGoC
Prove the whole chain end-to-end before Friday (the one-command solver is in
`ORGANIZER_FLAGS.md`):
- [ ] **Recon:** `curl -s http://<host-ip>/ | grep internal-portal` → path shows.
- [ ] **Guest:** `http://<host-ip>/internal-portal` loads, Admin Console locked.
- [ ] **Escalation:** signing key visible in `/static/js/session.js`; forged `admin` cookie unlocks the Admin Console (badge → Administrator).
- [ ] **IDOR:** `/internal-portal/incident/4663` returns the flag; the `View` button for #4663 is disabled in the dashboard (gap is intended).
- [ ] **Negative check:** as guest, `/internal-portal/admin` returns **403** (access control holds until escalation).

## G. Load & resilience — TECH
- [ ] ~10–40 concurrent hits stay responsive (`gunicorn` is set to 4 workers × 4 threads = 16 concurrent; tune via `GUNICORN_WORKERS`/`GUNICORN_THREADS` env if the Pi is hot).
- [ ] Pi thermals OK under load (heatsink/fan; `vcgencmd measure_temp` < ~75 °C). This app is light — CPU spikes are far more likely from **Nmap**, hence ↓
- [ ] **Polite-scan rule** in the player rules as the in-game "stealth" requirement: `-T2`, **no `-A`**, no aggressive timing against the host.
- [ ] Recovery move known: `docker compose restart` restores in seconds; `docker compose logs -f` to watch.

## H. Physical / hardware
- [ ] Pi on a **known-good 5V/3A (Pi 4) or official 27W USB-C (Pi 5)** supply — undervoltage is the #1 cause of flaky Pis under load.
- [ ] Wired uplink to the router if possible (frees Wi-Fi airtime for 40 participants).
- [ ] Router on its own clean channel; 2.4GHz + 5GHz both up; WPA2 on the closed SSID.
- [ ] SD card / SSD has free space (`df -h`); the app writes nothing, but Docker logs grow — log rotation or `--log-opt max-size=10m` if you're worried.

---

## Quick reference

```bash
# deploy / update
docker compose up -d --build
# rotate flag (after editing .env)
docker compose up -d
# health
curl -s localhost/health            # -> ok
# logs / restart / stop
docker compose logs -f
docker compose restart
docker compose down
```

| Item | Value |
|---|---|
| Host port (participants) | **80** → `http://<host-ip>/` |
| Container port (internal) | 8080 (non-root; don't change) |
| Hidden portal | `/internal-portal` |
| Flag location | incident report **#4663** |
| Flag rotate | `.env` → `FLAG=...` → `docker compose up -d` |
| Hardening in place | non-root, `cap_drop: ALL`, `no-new-privileges`, read-only FS + tmpfs |

## Definition of done
App runs **air-gapped**, a second device on the closed Wi-Fi solves the full
chain, and **CTFd accepts the rotated flag.** Anything failing on *rendering,
the vuln chain, or the flag* → back to organizers (code lane). Anything failing
on *Docker host, LAN, power, or CTFd* → your lane.
