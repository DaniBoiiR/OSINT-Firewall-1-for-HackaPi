"""
Aurelian Dynamics - "Aurelian Pulse" internal social feed
Hack-A-PI - Firewall 1 (OSINT / Information-Disclosure recon stage)

A deliberately information-leaking company social feed. Players perform OSINT
recon to recover real intel (the "loot") and pivot into Firewall 2. The answer
submitted to CTFd is the recovered intel itself, never a FLAG{...} string.

Intended disclosures, browser-and-LLM solvable only (no local tools needed):
  S1  profiling .......... correlate posts to find the insider (Aya); her staff
                          ID is on her profile.
  S2  forced browsing .... a post she thinks she deleted is still reachable by
                          URL. Most gaps are troll "deleted" pages; one holds
                          the SSO migration codename and points at /resources.
  S3  exposed directory .. robots.txt points at /resources/; a leftover note
                          leaks a staging host in plaintext.
  S4  data exposure ...... the same note hides the portal path in base64 (the
                          LLM decodes it). This path is Firewall 2's entry.
  S5  SVG source ......... a poster SVG hides a setup code; save it, read the
                          source, decode the base64 inside (bonus, hardest).

Security (everything NOT above is ordinary and safe): integer-only post routing
(no traversal/LFI), /resources served from a fixed whitelist (no arbitrary
reads), Jinja autoescaping on, no DB, no shell-out, no server-side session
state. Fully offline: no CDNs, fonts, or network calls.

Run (dev/event):  python app.py          # prints a LAN banner, serves via waitress
"""

import base64
import json
import os
import socket

from flask import (
    Flask,
    Response,
    abort,
    render_template,
    request,
    url_for,
)

import config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
IMG_DIR = os.path.join(BASE_DIR, "static", "img")

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

def _load(name):
    with open(os.path.join(DATA_DIR, name), encoding="utf-8") as fh:
        return json.load(fh)


PROFILES = _load("profiles.json")
POSTS = {p["id"]: p for p in _load("posts.json")}


def _b64(s: str) -> str:
    return base64.b64encode(s.encode("utf-8")).decode("ascii")


def _render_text(post):
    """Inject loot tokens into a post body (keeps loot out of the data file)."""
    text = post["text"]
    text = text.replace("__CODENAME__", config.LOOT["S2_CODENAME"])
    return text


def _view(post):
    v = dict(post)
    v["text"] = _render_text(post)
    v["profile"] = PROFILES.get(post["user"], {"name": post["user"], "color": "2563EB"})
    return v


# ---------------------------------------------------------------------------
# S5 assets: generate the poster SVGs at boot (loot stays rotatable).
# One poster hides the setup code as base64 inside <metadata>; the others are
# decoys so players cannot assume "an SVG always has the answer".
# ---------------------------------------------------------------------------

def _poster_svg(title, subtitle, accent, hidden_b64=None, troll_comment=None):
    meta = ""
    comment = ""
    if hidden_b64 is not None:
        # The real one: an "export note" left in the file. base64 so it needs a
        # decode step (the LLM), not just a glance.
        comment = "\n  <!-- export note (internal, do not ship): setup token below -->"
        meta = (
            "\n  <metadata id=\"export-notes\">"
            "\n    <note>launch checklist export - remove before publishing</note>"
            f"\n    <token encoding=\"base64\">{hidden_b64}</token>"
            "\n  </metadata>"
        )
    elif troll_comment is not None:
        comment = f"\n  <!-- {troll_comment} -->"

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450" width="800" height="450">'
        f"{comment}{meta}\n"
        f'  <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="#{accent}"/><stop offset="1" stop-color="#9333ea"/>'
        "</linearGradient></defs>\n"
        '  <rect width="800" height="450" fill="url(#g)"/>\n'
        '  <rect x="40" y="40" width="720" height="370" rx="18" fill="#ffffff" opacity="0.08"/>\n'
        f'  <text x="400" y="200" fill="#ffffff" font-family="sans-serif" font-size="54" '
        f'font-weight="bold" text-anchor="middle">{title}</text>\n'
        f'  <text x="400" y="260" fill="#e5e7eb" font-family="sans-serif" font-size="24" '
        f'text-anchor="middle">{subtitle}</text>\n'
        '  <text x="400" y="380" fill="#c7d2fe" font-family="sans-serif" font-size="18" '
        'text-anchor="middle">Aurelian Dynamics</text>\n'
        "</svg>\n"
    )


def generate_posters():
    os.makedirs(IMG_DIR, exist_ok=True)
    # Real one: hides the setup code as base64.
    with open(os.path.join(IMG_DIR, "launch-poster.svg"), "w", encoding="utf-8") as fh:
        fh.write(_poster_svg(
            "HACK DAY 2026", "Build. Break. Fix. Oct 20",
            "2563eb", hidden_b64=_b64(config.LOOT["S5_SETUP_CODE"])))
    # Decoy 1: totally clean.
    with open(os.path.join(IMG_DIR, "welcome-poster.svg"), "w", encoding="utf-8") as fh:
        fh.write(_poster_svg("WELCOME ABOARD", "New starters, floor 3", "0ea5e9"))
    # Decoy 2: has a troll comment, no loot.
    with open(os.path.join(IMG_DIR, "hackday-badge.svg"), "w", encoding="utf-8") as fh:
        fh.write(_poster_svg("HACK DAY", "Official Badge", "db2777",
                             troll_comment="you opened the source! good instinct. wrong file though :)"))


generate_posters()


# ---------------------------------------------------------------------------
# Template globals
# ---------------------------------------------------------------------------

@app.context_processor
def inject_globals():
    return {
        "COMPANY": config.COMPANY,
        "SITE_NAME": config.SITE_NAME,
        "suggested": [
            {"username": u, **p} for u, p in PROFILES.items() if p.get("suggested")
        ],
        "trends": [
            {"tag": "SSO cutover", "posts": "42 posts"},
            {"tag": "Hack Day 2026", "posts": "18 posts"},
            {"tag": "floor 2 gym", "posts": "7 posts"},
            {"tag": "shawarma wednesday", "posts": "5 posts"},
        ],
    }


# ---------------------------------------------------------------------------
# Feed / profiles / posts / search
# ---------------------------------------------------------------------------

@app.route("/")
def feed():
    listed = [p for p in POSTS.values() if p.get("kind") == "listed"]
    listed.sort(key=lambda p: p["ts"], reverse=True)
    return render_template("feed.html", posts=[_view(p) for p in listed], active="home")


@app.route("/profile/<username>")
def profile(username):
    prof = PROFILES.get(username)
    if prof is None:
        abort(404)

    user_posts = [
        _view(p)
        for p in sorted(POSTS.values(), key=lambda p: p["ts"], reverse=True)
        if p["user"] == username and p.get("kind") == "listed"
    ]
    # S1: Aya overshares her staff ID on her own profile.
    staff_id = config.LOOT["S1_STAFF_ID"] if prof.get("staff_id_loot") else None
    return render_template(
        "profile.html", username=username, profile=prof,
        posts=user_posts, staff_id=staff_id, active=None,
    )


@app.route("/post/<int:pid>")
def post(pid):
    # Integer-only route: no traversal, no filesystem access.
    p = POSTS.get(pid)
    if p is None:
        abort(404)  # genuinely missing id -> normal 404

    kind = p.get("kind")
    if kind == "deleted_troll":
        # A gap that LOOKS deleted and taunts the enumerator.
        return render_template("deleted.html", post=_view(p), active=None), 200
    # listed posts and the one hidden_real post render normally.
    return render_template("post.html", post=_view(p), active=None)


@app.route("/search")
def search():
    q = (request.args.get("q") or "").strip()
    post_hits, user_hits = [], []
    if q:
        ql = q.lower()
        for p in sorted(POSTS.values(), key=lambda p: p["ts"], reverse=True):
            if p.get("kind") != "listed":
                continue  # unlisted/deleted posts are not indexed
            name = PROFILES.get(p["user"], {}).get("name", "")
            if ql in (_render_text(p) + " " + p["user"] + " " + name).lower():
                post_hits.append(_view(p))
        for u, prof in PROFILES.items():
            if ql in (u + " " + prof["name"] + " " + prof["dept"] + " " +
                      prof.get("title", "") + " " + prof["bio"]).lower():
                user_hits.append({"username": u, **prof})
    return render_template("search.html", q=q, post_hits=post_hits,
                           user_hits=user_hits, active="search")


# ---------------------------------------------------------------------------
# S3 / S4: the exposed /resources folder (fixed whitelist, no traversal)
# ---------------------------------------------------------------------------

def _resources():
    host = config.LOOT["S3_STAGING_HOST"]
    portal_b64 = _b64(config.LOOT["S4_PORTAL_PATH"])
    troll_b64 = _b64("Q3 all-hands team-building survey (link expired, nobody filled it in)")

    return {
        "portal-migration-notes.txt": (
            "text/plain; charset=utf-8",
            (
                "SKYLINE migration - working notes (a.nocari)\n"
                "============================================\n"
                "left here so i do not lose them. will delete before anyone notices.\n"
                "\n"
                "- staging box is STILL up (kill this later): " + host + "\n"
                "- prod build: " + config.BUILD + "\n"
                "- prod portal was relocated off the main nav during the cutover.\n"
                "  wrote the path in base64 so Marwan does not clock it at a glance:\n"
                "      " + portal_b64 + "\n"
                "\n"
                "- corporate also sent this survey thing, pasting so i remember to ignore it:\n"
                "      " + troll_b64 + "\n"
                "\n"
                "note to self: encoding is NOT the same as hiding. fix this properly later.\n"
            ),
        ),
        "press-boilerplate.txt": (
            "text/plain; charset=utf-8",
            (
                "Aurelian Dynamics - approved press boilerplate.\n"
                "\"Intelligent Capital. Measurable Growth.\" Headquartered in the UAE,\n"
                "operating across 26 markets. Media enquiries: press@aureliandynamics.example\n"
                "(This file is public on purpose. Nothing sensitive here.)\n"
            ),
        ),
        "survey.txt": (
            "text/plain; charset=utf-8",
            (
                "internal survey export (archived)\n"
                "---------------------------------\n"
                + troll_b64 + "\n"
            ),
        ),
    }


@app.route("/resources/")
def resources_index():
    return render_template("dirlist.html", path="/resources/",
                           files=sorted(_resources().keys()), active=None)


@app.route("/resources/<path:filename>")
def resources_file(filename):
    entry = _resources().get(filename)
    if entry is None:
        abort(404)  # whitelist only - no traversal, no arbitrary reads
    mimetype, body = entry
    return Response(body, mimetype=mimetype)


@app.route("/robots.txt")
def robots():
    return Response(
        "User-agent: *\n"
        "Disallow: /resources/\n"
        "# nothing sensitive in there, honest\n",
        mimetype="text/plain",
    )


@app.route("/health")
def health():
    return Response("ok", mimetype="text/plain")


@app.errorhandler(404)
def not_found(_):
    return render_template("404.html", active=None), 404


# ---------------------------------------------------------------------------
# Run: print a Flask-style LAN banner, then serve with waitress (production).
# ---------------------------------------------------------------------------

def _lan_ip() -> str:
    """Best-effort LAN IP, works without internet (no packets actually sent)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
    except OSError:
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except OSError:
            ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def _banner():
    port = config.PORT
    lines = [
        f" * {config.SITE_NAME} - {config.COMPANY} (Firewall 1)",
        " * Running on all addresses (0.0.0.0)",
        f" * Running on http://127.0.0.1:{port}",
        f" * Running on http://{_lan_ip()}:{port}",
        "Press CTRL+C to quit",
    ]
    print("\n".join(lines), flush=True)


if __name__ == "__main__":
    _banner()
    try:
        from waitress import serve
        serve(app, host=config.HOST, port=config.PORT, threads=8)
    except ImportError:
        app.run(host=config.HOST, port=config.PORT, debug=False, threaded=True)
