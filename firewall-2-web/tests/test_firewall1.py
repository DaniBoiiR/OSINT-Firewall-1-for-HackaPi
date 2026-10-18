"""
Firewall 1 v3 test suite - connected chain (login + inbox + projects).

Verifies, browser-and-LLM-solvable only: each stage's loot is recoverable ONLY
at its intended point and acts as the key to the next stage, the trolls/decoys
behave, nothing leaks early, and the security negatives hold (no traversal, no
arbitrary reads, integer-only posts, signed login cookie not forgeable).

Run:  cd firewall1 && python -m pytest -q
"""

import base64
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import app as appmod  # noqa: E402

L = config.LOOT
REMOVED = L["S4_REMOVED_POST"]        # S4: the "deleted" post that is still live ("106")
SKY = L["S3_CODENAME"].lower()        # the project folder name


@pytest.fixture()
def client():
    appmod.app.config.update(TESTING=True)
    return appmod.app.test_client()


def text(r):
    return r.get_data(as_text=True)


def login_as(client, staff_id, password):
    return client.post("/login", data={"staff_id": staff_id, "password": password},
                       follow_redirects=False)


def aya(client):
    r = login_as(client, L["S1_STAFF_ID"], L["S2_PASSWORD"])
    assert r.status_code in (301, 302)
    return client


# ------------------------------------------------------------- basics --------

def test_feed_ok(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Aurelian Pulse" in text(r) and "Aurelian Dynamics" in text(r)


def test_health(client):
    assert text(client.get("/health")) == "ok"


def test_no_flag_strings_anywhere(client):
    for path in ["/", "/profile/a.nocari", "/search?q=portal", "/resources/",
                 "/resources/survey.txt", "/post/106", "/login"]:
        assert "FLAG{" not in text(client.get(path)), path


# ------------------------------------------------ S1: profile the insider ----

def test_S1_staff_id_on_aya_profile(client):
    r = client.get("/profile/a.nocari")
    assert r.status_code == 200
    assert L["S1_STAFF_ID"] in text(r)


def test_S1_aya_findable_by_search(client):
    for q in ("portal", "aya", "nocari", "intern"):
        assert "a.nocari" in text(client.get("/search", query_string={"q": q})), q


def test_S1_aya_not_in_suggested():
    assert "a.nocari" not in [u for u, p in appmod.PROFILES.items() if p.get("suggested")]


def test_S1_staff_id_not_on_feed(client):
    assert L["S1_STAFF_ID"] not in text(client.get("/"))


def test_S1_false_staff_id_present_but_distinct(client):
    assert config.FALSE_LOOT["FAKE_STAFF_ID"] in text(client.get("/"))
    assert config.FALSE_LOOT["FAKE_STAFF_ID"] != L["S1_STAFF_ID"]


# ------------------------------------------ S2: credential profiling ---------

def test_S2_password_clues_on_feed(client):
    body = text(client.get("/"))
    # the three "favourite things" are all discoverable in the public feed
    assert "Mochi" in body          # cat
    assert "matcha" in body.lower()  # drink
    assert "22" in body             # turned 22 -> 2004


def test_S2_password_itself_not_published(client):
    # The concatenated password must never appear verbatim anywhere public.
    for path in ("/", "/profile/a.nocari", "/search?q=password", "/login"):
        assert L["S2_PASSWORD"].lower() not in text(client.get(path)).lower(), path


def test_S2_correct_login_sets_cookie(client):
    r = login_as(client, L["S1_STAFF_ID"], L["S2_PASSWORD"])
    assert r.status_code in (301, 302)
    assert config.SESSION_COOKIE in r.headers.get("Set-Cookie", "")


def test_S2_login_is_case_and_space_insensitive(client):
    r = login_as(client, " adi-2291 ", "Mochi Matcha 2004")
    assert r.status_code in (301, 302)
    assert config.SESSION_COOKIE in r.headers.get("Set-Cookie", "")


def test_S2_wrong_password_valid_id_leaks_hint(client):
    r = login_as(client, L["S1_STAFF_ID"], "wrongwrong")
    assert r.status_code == 401
    assert config.PASSWORD_HINT in text(r)       # legacy hint disclosure
    assert config.SESSION_COOKIE + "=" not in r.headers.get("Set-Cookie", "")


def test_S2_username_enumeration_distinguishes_unknown_id(client):
    unknown = text(login_as(client, "ADI-7777", "whatever"))
    known = text(login_as(client, L["S1_STAFF_ID"], "whatever"))
    assert "No staff ID on file" in unknown
    assert "No staff ID on file" not in known    # known ID must NOT say that


def test_S2_expired_decoy_password(client):
    r = login_as(client, L["S1_STAFF_ID"], config.FALSE_LOOT["EXPIRED_PASS"])
    assert r.status_code == 401
    assert "expired" in text(r).lower()
    assert config.SESSION_COOKIE + "=" not in r.headers.get("Set-Cookie", "")


def test_S2_kiosk_decoy_logs_in_but_is_dead_end(client):
    r = login_as(client, config.FALSE_LOOT["KIOSK_USER"], config.FALSE_LOOT["KIOSK_PASS"])
    assert r.status_code in (301, 302)   # valid creds...
    # ...but kiosk cannot reach the SKYLINE folder
    r2 = client.get(f"/projects/{L['S3_CODENAME'].lower()}/")
    assert r2.status_code == 403


# ---------------------------------------- S3: private data (codename) --------

def test_S3_inbox_requires_login(client):
    r = client.get("/messages", follow_redirects=False)
    assert r.status_code in (301, 302)
    assert "/login" in r.headers.get("Location", "")


def test_S3_codename_in_aya_inbox(client):
    aya(client)
    body = text(client.get("/messages"))
    assert L["S3_CODENAME"] in body


def test_S3_codename_never_public(client):
    for path in ("/", "/profile/a.nocari", "/post/106",
                 "/search?q=skyline", "/resources/survey.txt"):
        assert L["S3_CODENAME"] not in text(client.get(path)), path


def test_S3_kiosk_inbox_has_no_codename(client):
    login_as(client, config.FALSE_LOOT["KIOSK_USER"], config.FALSE_LOOT["KIOSK_PASS"])
    assert L["S3_CODENAME"] not in text(client.get("/messages"))


# ---------------------------------------- S4: the removed-posts log ----------

def test_S4_projects_listing_disabled(client):
    aya(client)
    body = text(client.get("/projects/"))
    assert "disabled" in body.lower()
    # the codename must not be handed out by the index itself
    assert L["S3_CODENAME"].lower() not in body.lower() or "/projects/&lt;" in body


def test_S4_skyline_folder_lists_removed_log(client):
    # logged in as Aya, correct codename -> folder lists the removed-posts log
    aya(client)
    r = client.get(f"/projects/{SKY}/")
    assert r.status_code == 200
    assert "removed-posts.log" in text(r)


def test_S4_wrong_project_name_404(client):
    aya(client)
    assert client.get("/projects/marketing/").status_code == 404


def test_S4_log_flags_the_live_post_among_trolls(client):
    aya(client)
    body = text(client.get(f"/projects/{SKY}/removed-posts.log"))
    assert REMOVED in body                      # S4 loot: the still-live post id
    assert "STILL LIVE" in body
    for troll in ("103", "111", "113"):         # the trolls are listed as really deleted
        assert troll in body
    # the portal path itself is NOT in the log (it lives inside /post/106)
    assert L["S5_PORTAL_PATH"] not in body
    assert base64.b64encode(L["S5_PORTAL_PATH"].encode()).decode() not in body


def test_S4_log_requires_aya(client):
    login_as(client, config.FALSE_LOOT["KIOSK_USER"], config.FALSE_LOOT["KIOSK_PASS"])
    assert client.get(f"/projects/{SKY}/removed-posts.log").status_code == 403
    anon = appmod.app.test_client()
    assert anon.get(f"/projects/{SKY}/removed-posts.log").status_code in (301, 302)


# ---------------------------------------- S5: data exposure (F2 pivot) -------

def test_S5_post106_reveals_base64_to_aya(client):
    aya(client)
    body = text(client.get(f"/post/{REMOVED}"))
    assert L["S5_PORTAL_PATH"] not in body                               # not plaintext
    b64 = base64.b64encode(L["S5_PORTAL_PATH"].encode()).decode()
    assert b64 in body                                                   # base64 present for Aya
    assert base64.b64decode(b64).decode() == L["S5_PORTAL_PATH"] == "/internal-portal"


def test_S5_post106_hides_base64_from_anon_and_kiosk(client):
    b64 = base64.b64encode(L["S5_PORTAL_PATH"].encode()).decode()
    # anonymous: post opens (still live) but shows no base64 and no portal path
    anon = appmod.app.test_client()
    body = text(anon.get(f"/post/{REMOVED}"))
    assert anon.get(f"/post/{REMOVED}").status_code == 200
    assert b64 not in body and L["S5_PORTAL_PATH"] not in body
    # kiosk: same - valid login, but not Aya
    k = appmod.app.test_client()
    login_as(k, config.FALSE_LOOT["KIOSK_USER"], config.FALSE_LOOT["KIOSK_PASS"])
    kbody = text(k.get(f"/post/{REMOVED}"))
    assert b64 not in kbody and L["S5_PORTAL_PATH"] not in kbody


def test_S5_no_marker_leaks_in_rendered_post(client):
    # the raw template marker must never reach the page, logged in or out
    for cl in (client, appmod.app.test_client()):
        assert "__PORTAL_B64__" not in text(cl.get(f"/post/{REMOVED}"))
    aya(client)
    assert "__PORTAL_B64__" not in text(client.get(f"/post/{REMOVED}"))


# -------------------------------------------- S6: SVG source (bonus) ---------

def test_S6_real_poster_hides_base64_code(client):
    r = client.get("/static/img/launch-poster.svg")
    assert r.status_code == 200
    svg = text(r)
    assert L["S6_SETUP_CODE"] not in svg
    b64 = base64.b64encode(L["S6_SETUP_CODE"].encode()).decode()
    assert b64 in svg
    assert base64.b64decode(b64).decode() == L["S6_SETUP_CODE"]


def test_S6_decoy_posters_have_no_loot(client):
    for name in ("welcome-poster.svg", "hackday-badge.svg"):
        svg = text(client.get("/static/img/" + name))
        assert L["S6_SETUP_CODE"] not in svg
        assert base64.b64encode(L["S6_SETUP_CODE"].encode()).decode() not in svg


def test_S6_code_not_on_feed(client):
    assert L["S6_SETUP_CODE"] not in text(client.get("/"))


# ------------------------------------------------- forced browsing / trolls --

def test_hidden_post_106_opens_for_anon_without_loot(client):
    # The "deleted" post is still live (forced browse), but to an anonymous
    # visitor it shows only panic text - no codename, no portal path.
    r = client.get("/post/106")
    assert r.status_code == 200
    body = text(r)
    assert "removed" not in body.lower()      # not a troll page
    assert L["S3_CODENAME"] not in body       # codename never public
    assert L["S5_PORTAL_PATH"] not in body    # portal path gated to Aya


def test_troll_gaps_taunt_not_leak(client):
    for pid in (103, 111, 113):
        r = client.get(f"/post/{pid}")
        assert r.status_code == 200
        assert "removed" in text(r).lower() or "deleted" in text(r).lower()
        assert L["S3_CODENAME"] not in text(r)


def test_resources_is_decoy_dead_end(client):
    # robots points here; it exists; it holds nothing that advances the chain.
    assert "/resources/" in text(client.get("/robots.txt"))
    idx = text(client.get("/resources/"))
    assert "press-boilerplate.txt" in idx and "survey.txt" in idx
    for name in ("press-boilerplate.txt", "survey.txt"):
        body = text(client.get("/resources/" + name))
        assert L["S3_CODENAME"] not in body
        assert L["S5_PORTAL_PATH"] not in body


def test_troll_base64_decodes_to_junk(client):
    # gym caption (feed) and survey (resources) are decodable jokes, not loot.
    bodies = text(client.get("/")) + text(client.get("/resources/survey.txt"))
    toks = re.findall(r"[A-Za-z0-9+/]{16,}={0,2}", bodies)
    decoded = []
    for t in toks:
        try:
            decoded.append(base64.b64decode(t).decode())
        except Exception:
            pass
    assert any("gym" in d.lower() or "survey" in d.lower() for d in decoded)
    assert L["S5_PORTAL_PATH"] not in decoded


# ------------------------------------------------- security negatives --------

def test_login_cookie_not_forgeable(client):
    # Flipping the role in a self-made cookie without the server key must fail.
    import json
    forged_payload = base64.urlsafe_b64encode(
        json.dumps({"role": "aya", "username": "a.nocari", "display": "Aya Nocari"}).encode()
    ).decode().rstrip("=")
    forged = f"{forged_payload}.{'0' * 64}"
    client.set_cookie(config.SESSION_COOKIE, forged)
    r = client.get(f"/projects/{SKY}/removed-posts.log", follow_redirects=False)
    assert r.status_code in (301, 302)   # treated as logged-out, redirected to login
    # and the forged cookie must not unlock the gated post payload either
    assert base64.b64encode(L["S5_PORTAL_PATH"].encode()).decode() not in text(client.get(f"/post/{REMOVED}"))


def test_no_traversal_in_projects(client):
    aya(client)
    for bad in ("../../app.py", "../../config.py", "../../../etc/passwd"):
        r = client.get(f"/projects/{L['S3_CODENAME'].lower()}/" + bad)
        assert r.status_code in (301, 308, 404)
        assert "SESSION_KEY" not in text(r) and "def " not in text(r)


def test_no_traversal_in_resources(client):
    for bad in ("../config.py", "../app.py", "../../etc/passwd", "etc/passwd"):
        r = client.get("/resources/" + bad)
        assert r.status_code in (301, 308, 404)
        assert "LOOT" not in text(r) and "def " not in text(r)


def test_post_route_integer_only(client):
    assert client.get("/post/abc").status_code == 404
    assert client.get("/post/../app.py").status_code in (301, 308, 404)


def test_genuinely_missing_post_is_404(client):
    assert client.get("/post/999").status_code == 404


# ------------------------------------------------- offline / rotation --------

def test_no_external_urls():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hits = []
    for sub in ("templates", "static"):
        for dp, _, files in os.walk(os.path.join(root, sub)):
            for fn in files:
                if fn.endswith((".jpg", ".png", ".svg")):
                    continue
                body = open(os.path.join(dp, fn), encoding="utf-8", errors="ignore").read()
                for m in re.findall(r"https?://[^\s\"')]+", body):
                    if "aureliandynamics.example" not in m and "w3.org" not in m:
                        hits.append((fn, m))
    assert not hits, hits


def test_loot_rotatable(monkeypatch):
    import importlib
    monkeypatch.setenv("LOOT_S1", "ADI-9999")
    monkeypatch.setenv("LOOT_S3", "NIGHTFALL")
    cfg = importlib.reload(config)
    try:
        assert cfg.LOOT["S1_STAFF_ID"] == "ADI-9999"
        assert cfg.LOOT["S3_CODENAME"] == "NIGHTFALL"
    finally:
        # Restore defaults for any later test: drop the env FIRST, then reload,
        # so config does not stay mutated (it would, if reloaded while set).
        monkeypatch.delenv("LOOT_S1", raising=False)
        monkeypatch.delenv("LOOT_S3", raising=False)
        importlib.reload(config)


# ------------------------------------------------- UI polish (no-leak) -------

def test_notifications_page_ok(client):
    r = client.get("/notifications")
    assert r.status_code == 200
    body = text(r)
    assert "Notifications" in body
    # flavour only: must never leak any loot
    assert "FLAG{" not in body
    assert L["S3_CODENAME"] not in body
    assert L["S2_PASSWORD"].lower() not in body.lower()
    assert L["S5_PORTAL_PATH"] not in body


def test_compose_is_enabled(client):
    # The composer must be live (not the old disabled/read-only button).
    body = text(client.get("/"))
    assert "data-compose-submit" in body
    assert "Read-only during audit" not in body


def test_meme_image_served_and_referenced(client):
    assert client.get("/static/img/uploads/meme-1.png").status_code == 200
    assert "uploads/meme-1.png" in text(client.get("/"))


def test_notifications_in_nav(client):
    # the nav links to the real notifications route now, not back to the feed
    assert "/notifications" in text(client.get("/"))


# ------------------------------------------------- auth pages / nav ----------

def test_login_is_standalone_page(client):
    # A proper login page: its own centered layout, NOT wrapped in the feed chrome.
    body = text(client.get("/login"))
    assert "Staff sign in" in body
    assert "Who to follow" not in body      # no right sidebar
    assert "What's happening" not in body   # no trends panel
    assert 'name="staff_id"' in body and 'name="password"' in body


def test_logout_page_and_cookie_cleared(client):
    aya(client)
    r = client.get("/logout")
    assert r.status_code == 200
    assert "signed out" in text(r).lower()
    # cookie is cleared, so the next protected request is anonymous again
    fresh = appmod.app.test_client()
    assert fresh.get("/messages", follow_redirects=False).status_code in (301, 302)


def test_messages_link_hidden_when_logged_out(client):
    assert "/messages" not in text(client.get("/"))      # anon: no Messages nav link
    aya(client)
    assert "/messages" in text(client.get("/"))          # logged in: it appears


def test_removed_log_points_to_the_live_post(client):
    # the chain reads: log flags #106 as still live -> open /post/106 -> base64
    aya(client)
    log = text(client.get(f"/projects/{SKY}/removed-posts.log"))
    assert f"/post/{REMOVED}" in log
    assert base64.b64encode(L["S5_PORTAL_PATH"].encode()).decode() in text(client.get(f"/post/{REMOVED}"))


def test_composer_present_and_no_broken_preview(client):
    body = text(client.get("/"))
    assert "data-compose-submit" in body
    # preview is hidden by default (class-toggled), not a stray visible box
    assert "data-compose-preview" in body
    assert "compose-count" in body
