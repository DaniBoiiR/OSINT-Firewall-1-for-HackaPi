"""
Aurelian Dynamics - "Aurelian Pulse" internal social feed
Hack-A-PI - Firewall 1 (OSINT / Information-Disclosure recon stage)

This firewall is a pentest reconnaissance exercise, not a flag hunt. Players
exploit information disclosure on a company social feed and the submitted answer
is the real intel they recover (a staff ID, a codename, a host, a path, a code).
No FLAG{...} strings anywhere.

All loot values are read from the environment so they rotate per event without
touching code or content. An unset/empty value falls back to the default.
"""

import os

COMPANY = "Aurelian Dynamics"
SITE_NAME = "Aurelian Pulse"

# Firewall 2 handoff facts. These are the REAL values F2 uses; Stage 4 discloses
# them so recon (F1) pivots cleanly into exploitation (F2).
BUILD = "adi-portal@2.3.1"
PORTAL_PATH = "/internal-portal"


def _val(env_name: str, default: str) -> str:
    return os.environ.get(env_name) or default


# ---- Loot: the real intel players recover and submit to CTFd ----------------
# Stage 4 (PORTAL_PATH) is the token that unlocks Firewall 2.
LOOT = {
    "S1_STAFF_ID": _val("LOOT_S1", "ADI-2291"),                     # on Aya's profile
    "S2_CODENAME": _val("LOOT_S2", "SKYLINE"),                      # in the hidden post
    "S3_STAGING_HOST": _val("LOOT_S3", "portal-stg.adi.internal"),  # plaintext in the note
    "S4_PORTAL_PATH": PORTAL_PATH,                                  # base64 in the note -> unlocks F2
    "S5_SETUP_CODE": _val("LOOT_S5", "adi-setup-override-7731"),    # hidden in an SVG poster
}

# ---- Decoys (CTFd rejects these; documented so volunteers know) -------------
FALSE_LOOT = {
    "FAKE_STAFF_ID": "ADI-0001",          # CEO's joke post
    "FAKE_PORTAL_PATH": "/employee-dashboard",  # Theo's "back in my day" post
}

# ---- Network. Default 5000 so it never clashes with Firewall 2 (host :80). --
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "5000"))
