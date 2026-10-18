"""
Aurelian Dynamics - "Aurelian Pulse" internal social feed
Hack-A-PI - Firewall 1 (OSINT / Information-Disclosure recon stage)

A deliberately information-leaking company social feed. Players perform OSINT
recon to recover real intel (the "loot") and pivot into Firewall 2. The answer
submitted to CTFd is the recovered intel itself, never a FLAG{...} string.

CONNECTED CHAIN - each loot is the literal key to the next stage:
  S1 profiling ...... correlate the feed to find the insider (Aya); her staff
                      ID is overshared on her profile. It is the login USERNAME.
  S2 cred profiling . she brags her password is "all my favourite things" and
                      leaks those things across her posts (cat, matcha, age).
                      The recovered password LOGS YOU IN as her.
  S3 priv data ...... logged in, her inbox reveals the migration codename
                      SKYLINE. That is the PROJECT FOLDER name: /projects/skyline/.
  S4 removed post ... that folder holds removed-posts.log; the trolls are really
                      deleted but #106 is UNLISTED and still live at /post/106.
  S5 data exposure .. /post/106, opened as Aya, hides the relocated portal path
                      in base64 (the LLM decodes it). /internal-portal is F2's entry.
  S6 SVG source ..... a poster SVG hides a setup code (bonus, hardest).

Security (everything NOT above is ordinary and safe): integer-only post routing
(no traversal/LFI), /resources and /projects served from fixed whitelists (no
arbitrary reads), signed stateless login cookie with a server-only key (no
cookie forging), Jinja autoescaping on, no DB, no shell-out. Fully offline.

Run (dev/event):  python app.py          # prints a LAN banner, serves via waitress
"""

import base64
import hashlib
import hmac
import json
import os
import socket

from flask import (
    Flask,
    Response,
    abort,
    make_response,
    redirect,
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
INBOX = _load("inbox.json")


def _b64(s: str) -> str:
    return base64.b64encode(s.encode("utf-8")).decode("ascii")


def _inject(text: str) -> str:
    """Rotatable codename stays out of the data files."""
    return text.replace("__CODENAME__", config.LOOT["S3_CODENAME"])


def _view(post):
    v = dict(post)
    v["text"] = _inject(post["text"])
    v["profile"] = PROFILES.get(post["user"], {"name": post["user"], "color": "2563EB"})
    return v


# ---------------------------------------------------------------------------
# Login: signed, stateless cookie. The signing key is SERVER-ONLY (never served
# to the client), so this is a credential-recovery challenge, not a forging one.
# ---------------------------------------------------------------------------

def _sign(payload: str) -> str:
    return hmac.new(config.SESSION_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()


def make_token(claims: dict) -> str:
    payload = base64.urlsafe_b64encode(
        json.dumps(claims, separators=(",", ":"), sort_keys=True).encode()
    ).decode().rstrip("=")
    return f"{payload}.{_sign(payload)}"


def read_token(token: str):
    if not token or "." not in token:
        return None
    payload, _, sig = token.rpartition(".")
    if not hmac.compare_digest(sig, _sign(payload)):
        return None
    try:
        pad = "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload + pad))
    except (ValueError, json.JSONDecodeError):
        return None


def current_session():
    return read_token(request.cookies.get(config.SESSION_COOKIE, "")) or {}


def _canon_id(s: str) -> str:
    return (s or "").replace(" ", "").upper()


def _canon_pw(s: str) -> str:
    return (s or "").replace(" ", "").lower()


# ---------------------------------------------------------------------------
# S6 assets: generate the poster SVGs at boot (loot stays rotatable).
# One poster hides the setup code as base64 inside <metadata>; the others are
# decoys so players cannot assume "an SVG always has the answer".
# ---------------------------------------------------------------------------

def _poster_svg(title, subtitle, accent, hidden_b64=None, troll_comment=None):
    meta = ""
    comment = ""
    if hidden_b64 is not None:
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
    with open(os.path.join(IMG_DIR, "launch-poster.svg"), "w", encoding="utf-8") as fh:
        fh.write(_poster_svg(
            "HACK DAY 2026", "Build. Break. Fix. Oct 20",
            "2563eb", hidden_b64=_b64(config.LOOT["S6_SETUP_CODE"])))
    with open(os.path.join(IMG_DIR, "welcome-poster.svg"), "w", encoding="utf-8") as fh:
        fh.write(_poster_svg("WELCOME ABOARD", "New starters, floor 3", "0ea5e9"))
    with open(os.path.join(IMG_DIR, "hackday-badge.svg"), "w", encoding="utf-8") as fh:
        fh.write(_poster_svg("HACK DAY", "Official Badge", "db2777",
                             troll_comment="you opened the source! good instinct. wrong file though :)"))


generate_posters()


# ---------------------------------------------------------------------------
# Template globals
# ---------------------------------------------------------------------------

@app.context_processor
def inject_globals():
    sess = current_session()
    return {
        "COMPANY": config.COMPANY,
        "SITE_NAME": config.SITE_NAME,
        "session_user": sess.get("display"),
        "session_role": sess.get("role"),
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

    if p.get("kind") == "deleted_troll":
        return render_template("deleted.html", post=_view(p), active=None), 200

    v = _view(p)
    # S5: the "unlisted but still live" post reveals the relocated portal path,
    # base64-encoded - but ONLY to Aya's session. Logged out / kiosk see the
    # panic text with no base64, so the path cannot leak ahead of the chain.
    if p.get("kind") == "hidden_real":
        if current_session().get("role") == "aya":
            reveal = ("\n\nrelocated prod portal path (base64 so it is not obvious): "
                      + _b64(config.LOOT["S5_PORTAL_PATH"]))
        else:
            reveal = ""
        v["text"] = v["text"].replace("__PORTAL_B64__", reveal)
    return render_template("post.html", post=v, active=None)


@app.route("/notifications")
def notifications():
    # Fictional, in-character activity. Pure flavour: no loot, no clues.
    items = [
        {"user": "theo.b", "kind": "mention",
         "text": "mentioned you in a thread about the SSO cutover.", "ts": "2026-10-15 13:16"},
        {"user": "mira.design", "kind": "post",
         "text": "posted new Hack Day 2026 posters.", "ts": "2026-10-15 11:30"},
        {"user": "r.aurelian", "kind": "like",
         "text": "and 11 others liked a post you follow.", "ts": "2026-10-15 09:40"},
        {"user": "lina.trails", "kind": "follow",
         "text": "started following you.", "ts": "2026-10-14 18:02"},
        {"user": "sam.eats", "kind": "like",
         "text": "liked your reaction to shawarma wednesday.", "ts": "2026-10-14 13:05"},
        {"user": "val.finance", "kind": "post",
         "text": "posted: Q3 close is done.", "ts": "2026-10-14 17:50"},
    ]
    for it in items:
        it["profile"] = PROFILES.get(it["user"], {"name": it["user"], "color": "2563EB"})
    sys_notice = ("Aurelian Pulse is in read-only mode for everyone except you during the "
                  "scheduled security audit. Your drafts stay on this device.")
    return render_template("notifications.html", items=items, sys_notice=sys_notice,
                           active="notifications")


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
            if ql in (_inject(p["text"]) + " " + p["user"] + " " + name).lower():
                post_hits.append(_view(p))
        for u, prof in PROFILES.items():
            if ql in (u + " " + prof["name"] + " " + prof["dept"] + " " +
                      prof.get("title", "") + " " + prof["bio"]).lower():
                user_hits.append({"username": u, **prof})
    return render_template("search.html", q=q, post_hits=post_hits,
                           user_hits=user_hits, active="search")


# ---------------------------------------------------------------------------
# S1 -> S2: staff login (credential recovery)
# ---------------------------------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    nxt = request.args.get("next") or request.form.get("next") or url_for("messages")
    if request.method == "GET":
        if current_session():
            return redirect(nxt)
        return render_template("login.html", active="login", next=nxt,
                               error=None, hint=None, attempts=None)

    staff_id = _canon_id(request.form.get("staff_id"))
    password = _canon_pw(request.form.get("password"))
    acct = config.ACCOUNTS.get(staff_id)

    # Username enumeration is intentional here (a realistic info-disclosure bug):
    # an unknown staff ID says so, a known one does not.
    if acct is None:
        return render_template("login.html", active="login", next=nxt,
                               error="No staff ID on file. Check your badge.",
                               hint=None, attempts=None), 401

    if _canon_pw(acct["password"]) == password:
        claims = {"username": acct["username"], "role": acct["role"], "display": acct["display"]}
        resp = make_response(redirect(nxt))
        resp.set_cookie(config.SESSION_COOKIE, make_token(claims), httponly=True, samesite="Lax")
        return resp

    if acct.get("expired_password") and _canon_pw(acct["expired_password"]) == password:
        return render_template("login.html", active="login", next=nxt,
                               error="That password expired on last rotation. Set a new one with IT.",
                               hint=None, attempts=None), 401

    # Valid ID, wrong password: legacy "password hint" self-service leaks here.
    hint = config.PASSWORD_HINT if acct["role"] == "aya" else None
    return render_template("login.html", active="login", next=nxt,
                           error="Incorrect password.",
                           hint=hint, attempts="2 login attempts remaining before lockout"), 401


@app.route("/logout")
def logout():
    resp = make_response(render_template("logout.html", active=None))
    resp.delete_cookie(config.SESSION_COOKIE)
    return resp


@app.route("/messages")
def messages():
    sess = current_session()
    if not sess:
        return redirect(url_for("login", next=url_for("messages")))
    threads = INBOX.get(sess.get("role"), [])
    # Inject the rotatable codename into message bodies.
    threads = json.loads(_inject(json.dumps(threads)))
    return render_template("inbox.html", active="messages", threads=threads,
                           me=sess.get("display"))


# ---------------------------------------------------------------------------
# S3 -> S4 -> S5: the gated /projects tree. Login required; listing disabled;
# the SKYLINE folder is member-only; the config file is unlisted (forced browse).
# ---------------------------------------------------------------------------

def _skyline_files():
    """The exposed SKYLINE project folder (member-only). It holds Aya's panic
    export of her "removed" posts. S4: the log shows the trolls are really
    deleted but #106 is UNLISTED and still live. S5: opening /post/106 (as Aya)
    reveals the relocated portal path, base64-encoded."""
    real = config.LOOT["S4_REMOVED_POST"]
    log = (
        "removal queue export - SKYLINE cleanup (a.nocari)\n"
        "=================================================\n"
        "exported my \"removed\" posts so i can actually delete them before Marwan's\n"
        "review. turns out unlisting just hides them from my profile. they still\n"
        "open by URL. cool. cool cool cool.\n"
        "\n"
        "  [removed]   #103   \"was a dumb joke\"        -> deleted\n"
        "  [removed]   #111   \"ratio'd myself lol\"     -> deleted\n"
        "  [removed]   #113   \"typo, reposted it\"      -> deleted\n"
        "  [UNLISTED]  #" + real + "   \"the portal confession\"  -> STILL LIVE at /post/"
        + real + "   <-- DELETE THIS, it still opens\n"
        "\n"
        "note to self: unlist is NOT delete. go actually remove #" + real + ".\n"
    )
    return {"removed-posts.log": ("text/plain; charset=utf-8", log)}


def _require_login():
    if not current_session():
        return redirect(url_for("login", next=request.path))
    return None


def _skyline_gate(project):
    """Shared gate for every /projects/<project>/... route. Returns a response
    to short-circuit with, or None to proceed."""
    gate = _require_login()
    if gate:
        return gate
    if project.lower() != config.LOOT["S3_CODENAME"].lower():
        abort(404)  # no such project
    if current_session().get("role") != "aya":
        abort(403)  # logged in, but not a member of project SKYLINE
    return None


@app.route("/projects/")
def projects_index():
    gate = _require_login()
    if gate:
        return gate
    # Listing is disabled: the directory exists but you cannot enumerate it.
    # You need the project's name (the SKYLINE codename from the inbox).
    return render_template("projects.html", active=None), 200


@app.route("/projects/<project>/")
def project_dir(project):
    gate = _skyline_gate(project)
    if gate:
        return gate
    files = _skyline_files()
    url_base = f"/projects/{project.lower()}/"
    return render_template("dirlist.html", path=url_base, url_base=url_base,
                           files=sorted(files.keys()), dirs=[],
                           project=project.lower(), active=None)


@app.route("/projects/<project>/<path:filename>")
def project_file(project, filename):
    gate = _skyline_gate(project)
    if gate:
        return gate
    entry = _skyline_files().get(filename)
    if entry is None:
        abort(404)  # whitelist only - no traversal, no arbitrary reads
    mimetype, body = entry
    return Response(body, mimetype=mimetype)


# ---------------------------------------------------------------------------
# /resources: a DECOY exposed directory. robots.txt points here, players find
# it, but it is a dead end (press boilerplate + a troll survey). Teaches that an
# exposed directory is not automatically useful. The REAL leak is /projects.
# ---------------------------------------------------------------------------

def _resources():
    troll_b64 = _b64("Q3 all-hands team-building survey (link expired, nobody filled it in)")
    return {
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
    return render_template("dirlist.html", path="/resources/", url_base="/resources/",
                           files=sorted(_resources().keys()), dirs=[], project=None, active=None)


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
        "Disallow: /projects/\n"
        "# nothing sensitive in there, honest\n",
        mimetype="text/plain",
    )


@app.route("/health")
def health():
    return Response("ok", mimetype="text/plain")


@app.errorhandler(403)
def forbidden(_):
    return render_template("403.html", active=None), 403


@app.errorhandler(404)
def not_found(_):
    return render_template("404.html", active=None), 404


# ---------------------------------------------------------------------------
# Run: print a Flask-style LAN banner, then serve with waitress (production).
# ---------------------------------------------------------------------------

def _lan_ip() -> str:
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
