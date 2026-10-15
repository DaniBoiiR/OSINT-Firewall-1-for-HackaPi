"""
Firewall 1 v2 test suite.

Verifies, browser-and-LLM-solvable only: each stage's loot is recoverable at its
intended point, the trolls/false-loot behave, nothing leaks early, and the
security negatives hold (no traversal, no arbitrary reads, integer-only posts).

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


@pytest.fixture()
def client():
    appmod.app.config.update(TESTING=True)
    return appmod.app.test_client()


def text(r):
    return r.get_data(as_text=True)


# ------------------------------------------------------------- basics --------

def test_feed_ok(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Aurelian Pulse" in text(r) and "Aurelian Dynamics" in text(r)


def test_health(client):
    assert text(client.get("/health")) == "ok"


def test_no_flag_strings_anywhere(client):
    # Pentest framing: there must be no FLAG{...} tokens in any player-facing page.
    for path in ["/", "/profile/a.nocari", "/search?q=portal", "/resources/",
                 "/resources/portal-migration-notes.txt", "/post/106"]:
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
    # The decoy ADI-0001 is visible (CEO post) and must differ from the real one.
    assert config.FALSE_LOOT["FAKE_STAFF_ID"] in text(client.get("/"))
    assert config.FALSE_LOOT["FAKE_STAFF_ID"] != L["S1_STAFF_ID"]


# ---------------------------------------------- S2: forced browsing ----------

def test_S2_hidden_post_has_codename(client):
    r = client.get("/post/106")
    assert r.status_code == 200
    assert L["S2_CODENAME"] in text(r)
    assert "/resources" in text(r)  # points to the next stage


def test_S2_hidden_post_not_listed(client):
    assert L["S2_CODENAME"] not in text(client.get("/"))
    assert L["S2_CODENAME"] not in text(client.get("/profile/a.nocari"))
    assert L["S2_CODENAME"] not in text(client.get("/search", query_string={"q": "skyline"}))


def test_S2_troll_gaps_taunt_not_leak(client):
    for pid in (103, 111, 113):
        r = client.get(f"/post/{pid}")
        assert r.status_code == 200
        assert "removed" in text(r).lower() or "deleted" in text(r).lower()
        assert L["S2_CODENAME"] not in text(r)


def test_S2_real_gap_distinct_from_trolls(client):
    assert "removed" not in text(client.get("/post/106")).lower()


# ---------------------------------------------- S3: exposed directory --------

def test_S3_robots_points_to_resources(client):
    assert "/resources/" in text(client.get("/robots.txt"))


def test_S3_dir_lists_notes(client):
    body = text(client.get("/resources/"))
    assert "portal-migration-notes.txt" in body


def test_S3_staging_host_in_note(client):
    r = client.get("/resources/portal-migration-notes.txt")
    assert r.status_code == 200
    assert L["S3_STAGING_HOST"] in text(r)


# -------------------------------------------- S4: data exposure (F2 pivot) ---

def test_S4_portal_path_is_base64_only(client):
    body = text(client.get("/resources/portal-migration-notes.txt"))
    assert L["S4_PORTAL_PATH"] not in body               # not plaintext
    assert base64.b64encode(L["S4_PORTAL_PATH"].encode()).decode() in body  # base64 present
    assert config.BUILD in body                           # build is plaintext context


def test_S4_decodes_to_portal_path(client):
    body = text(client.get("/resources/portal-migration-notes.txt"))
    b64 = base64.b64encode(L["S4_PORTAL_PATH"].encode()).decode()
    assert base64.b64decode(b64).decode() == L["S4_PORTAL_PATH"] == "/internal-portal"


def test_S4_troll_base64_decodes_to_junk(client):
    body = text(client.get("/resources/portal-migration-notes.txt"))
    # find all base64-looking tokens; at least one must NOT decode to the portal path
    toks = re.findall(r"[A-Za-z0-9+/]{16,}={0,2}", body)
    decoded = []
    for t in toks:
        try:
            decoded.append(base64.b64decode(t).decode())
        except Exception:
            pass
    assert L["S4_PORTAL_PATH"] in decoded
    assert any("survey" in d.lower() for d in decoded)  # the troll blob


# -------------------------------------------- S5: SVG source (bonus) ---------

def test_S5_real_poster_hides_base64_code(client):
    r = client.get("/static/img/launch-poster.svg")
    assert r.status_code == 200
    svg = text(r)
    assert L["S5_SETUP_CODE"] not in svg                  # not plaintext
    b64 = base64.b64encode(L["S5_SETUP_CODE"].encode()).decode()
    assert b64 in svg                                     # hidden as base64
    assert base64.b64decode(b64).decode() == L["S5_SETUP_CODE"]


def test_S5_decoy_posters_have_no_loot(client):
    for name in ("welcome-poster.svg", "hackday-badge.svg"):
        svg = text(client.get("/static/img/" + name))
        assert L["S5_SETUP_CODE"] not in svg
        assert base64.b64encode(L["S5_SETUP_CODE"].encode()).decode() not in svg


def test_S5_code_not_on_feed(client):
    assert L["S5_SETUP_CODE"] not in text(client.get("/"))


# ------------------------------------------------- security negatives --------

def test_no_traversal_in_resources(client):
    for bad in ("../config.py", "../app.py", "../../etc/passwd",
                "portal-migration-notes.txt/../../app.py", "etc/passwd"):
        r = client.get("/resources/" + bad)
        assert r.status_code in (301, 308, 404)
        assert "LOOT" not in text(r) and "def " not in text(r)


def test_post_route_integer_only(client):
    assert client.get("/post/abc").status_code == 404
    assert client.get("/post/../app.py").status_code in (301, 308, 404)


def test_unknown_resource_404(client):
    assert client.get("/resources/secret.txt").status_code == 404


def test_genuinely_missing_post_is_404(client):
    # A gap with no entry at all is a normal 404, not a troll page.
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
    monkeypatch.setenv("LOOT_S1", "ADI-9999")
    import importlib
    cfg = importlib.reload(config)
    assert cfg.LOOT["S1_STAFF_ID"] == "ADI-9999"
    importlib.reload(config)
