"""
Aurelian Dynamics - "Aurelian Pulse" internal social feed
Hack-A-PI - Firewall 1 (OSINT / Information-Disclosure recon stage)

This firewall is a pentest reconnaissance exercise, not a flag hunt. Players
exploit information disclosure on a company social feed and the submitted answer
is the real intel they recover (a staff ID, a password, a codename, a host, a
path, a code). No FLAG{...} strings anywhere.

CONNECTED CHAIN - each loot is the literal key to the next stage:
  S1  staff ID .......... ADI-2291 is Aya's login USERNAME
  S2  password .......... mochimatcha2004 (profiled from her posts) LOGS YOU IN
  S3  codename .......... SKYLINE (seen only in her inbox once logged in) is the
                          PROJECT FOLDER name -> /projects/skyline/
  S4  removed post ...... removed-posts.log lists her "deleted" posts; the trolls
                          are really gone, #106 is UNLISTED and STILL LIVE
  S5  portal path ....... open /post/106 (as Aya) -> base64 -> /internal-portal,
                          which UNLOCKS F2
  S6  setup code ........ bonus, hidden in a poster SVG

All loot values are read from the environment so they rotate per event without
touching code or content. An unset/empty value falls back to the default.
"""

import os

COMPANY = "Aurelian Dynamics"
SITE_NAME = "Aurelian Pulse"

# Firewall 2 handoff facts. These are the REAL values F2 uses; the end of the
# F1 chain discloses the portal path so recon (F1) pivots cleanly into
# exploitation (F2). Keep consistent with the frozen F2 build.
BUILD = "adi-portal@2.3.1"
PORTAL_PATH = "/internal-portal"


def _val(env_name: str, default: str) -> str:
    return os.environ.get(env_name) or default


# ---- Loot: the real intel players recover and submit to CTFd ----------------
# S5 (PORTAL_PATH) is the token that unlocks Firewall 2.
LOOT = {
    "S1_STAFF_ID": _val("LOOT_S1", "ADI-2291"),                      # on Aya's profile -> username
    "S2_PASSWORD": _val("LOOT_S2", "mochimatcha2004"),               # profiled from posts -> login
    "S3_CODENAME": _val("LOOT_S3", "SKYLINE"),                       # in her inbox -> folder name
    "S4_REMOVED_POST": _val("LOOT_S4", "106"),                       # the "deleted" post still live
    "S5_PORTAL_PATH": PORTAL_PATH,                                   # base64 inside /post/106 -> unlocks F2
    "S6_SETUP_CODE": _val("LOOT_S6", "adi-setup-override-7731"),     # bonus, in an SVG poster
}

# ---- Decoys (CTFd rejects these; documented so volunteers know) -------------
FALSE_LOOT = {
    "FAKE_STAFF_ID": "ADI-0001",                 # CEO's joke post
    "FAKE_PORTAL_PATH": "/employee-dashboard",   # Theo's "back in my day" post
    "KIOSK_USER": "ADI-1001",                    # sticky-note creds: real login, useless account
    "KIOSK_PASS": "Welcome123!",
    "EXPIRED_PASS": "sunshine2004",              # Aya's old password: near miss, "expired"
}

# Password hint deliberately disclosed when a VALID staff ID is given with the
# wrong password (a realistic "legacy self-service hint" info-disclosure bug).
# Order matches how the password concatenates: cat + drink + birth year.
PASSWORD_HINT = "\U0001F431\U0001F375\U0001F382"  # cat, matcha/teacup, birthday cake

# ---- Login / session --------------------------------------------------------
# F1 runs its OWN signed-cookie session, INDEPENDENT of Firewall 2. This key is
# never served to the client (F1 is a credential-recovery challenge, not a
# cookie-forging one), so F2's leaked signing trick cannot be used to skip the
# F1 login. Rotatable; a fresh random key per boot also works if unset.
SESSION_KEY = _val("F1_SESSION_KEY", "aurelian-pulse-f1-sess-9e2c1a")
SESSION_COOKIE = "pulse_session"

# Credential table: staff_id (canonical) -> account. "role" drives access.
#   aya   -> full insider access (inbox + /projects/skyline/)
#   kiosk -> logs in, but a dead-end shared account (teaches: valid != useful)
ACCOUNTS = {
    LOOT["S1_STAFF_ID"].replace(" ", "").upper(): {
        "password": LOOT["S2_PASSWORD"],
        "expired_password": FALSE_LOOT["EXPIRED_PASS"],
        "role": "aya",
        "username": "a.nocari",
        "display": "Aya Nocari",
    },
    FALSE_LOOT["KIOSK_USER"].replace(" ", "").upper(): {
        "password": FALSE_LOOT["KIOSK_PASS"],
        "expired_password": None,
        "role": "kiosk",
        "username": "floor2.kiosk",
        "display": "Floor 2 Kiosk (shared)",
    },
}

# ---- Network. Default 5000 so it never clashes with Firewall 2 (host :80). --
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "5000"))
