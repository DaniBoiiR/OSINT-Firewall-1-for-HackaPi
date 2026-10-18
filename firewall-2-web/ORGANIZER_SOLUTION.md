# Firewall 1 - ORGANIZERS ONLY - Loot & Full Solve
Keep OFF the player network and out of the Go-Bag. Not needed at runtime.

Base (dev): http://127.0.0.1:5000 (replace with the event host/port).

## Loot to load into CTFd (defaults; rotate via .env)
| Stage | Submit string | Technique | Gate |
|---|---|---|---|
| S1 | `ADI-2291` | profiling | unlocks S2 |
| S2 | `mochimatcha2004` | credential profiling | unlocks S3 |
| S3 | `SKYLINE` | private-data disclosure (login) | unlocks S4 |
| S4 | `106` | the "deleted" post still live (removed-posts.log) | unlocks S5 |
| S5 | `/internal-portal` | data exposure (base64 in /post/106) | **unlocks Firewall 2** |
| S6 | `adi-setup-override-7731` | SVG metadata | bonus, no gate |

Set CTFd answer matching to case-insensitive. S5 is the token that opens the F2
challenge card (set F2's prerequisite to S5). S6 has no dependents.

**The chain is connected - each loot is the literal key to the next stage:**
staff ID = the login username -> password = logs you in -> codename = the folder
name -> removed-posts.log = which "deleted" post is still live (#106) -> open
/post/106 (as Aya) -> base64 = the portal path = F2's door.

## Decoys the scoreboard must REJECT (do not add these as accepted answers)
- `ADI-0001` (CEO post #101) - fake staff ID.
- `/employee-dashboard` (Theo post #116) - fake portal path.
- `ADI-1001` / `Welcome123!` (Omar post #119) - real creds, dead-end kiosk account.
- `sunshine2004` (Aya post #117) - her old password, expired.

## Full solve
**S1 - profiling.** Aya (@a.nocari) is not in "Who to follow". Posts #104/#107/#108 point at the panicking intern. Search "portal"/"intern" -> her profile -> Staff ID `ADI-2291`. This is her login username.

**S2 - credential profiling.** She brags (post #120) her password is "all my favourite things." Gather them from the feed:
- #122 cat **Mochi** + **matcha**
- #123 "turned **22**" this year -> 2026 - 22 = **2004**
- Password = `mochimatcha2004` (login is case- and space-insensitive, so `Mochi Matcha 2004` also works).
- Confirmation bug: entering `ADI-2291` with any wrong password leaks the hint glyphs 🐱🍵🎂 on the login page (valid-ID-only; a realistic "self-service hint" disclosure).
- Decoys: `ADI-1001`/`Welcome123!` log into a useless kiosk; `sunshine2004` is "expired".

**S3 - private data (login required).** Log in as Aya -> **Messages**. The thread with Theo reveals the migration codename `SKYLINE` and that the real notes were moved into "the project folder, named after the migration". Public pages never contain `SKYLINE`.

**S4 - the "deleted" post that still opens.** `/robots.txt` disallows `/projects/`. `/projects/` listing is **disabled** (you need the codename). Go to `/projects/skyline/` (members only; you are Aya) and open `removed-posts.log` - Aya's export of her "removed" posts. The trolls (#103, #111, #113) are really deleted, but **#106** is flagged `UNLISTED -> STILL LIVE at /post/106`. The S4 loot is **`106`** (the post that unlisting never actually removed). Ties to Theo's DM: "your deleted post still opens."

**S5 - data exposure (F2 pivot).** Open `/post/106` while logged in as Aya. The body reveals the relocated portal path, base64:
```
echo 'L2ludGVybmFsLXBvcnRhbA==' | base64 -d      # -> /internal-portal
```
Submitting `/internal-portal` unlocks F2. (The LLM decodes the base64.) The base64 is shown **only to Aya's session** - logged out or on the kiosk account, `/post/106` opens but shows only the panic text, so the path cannot leak ahead of the chain.

**S6 (bonus) - SVG metadata.** Mira posts 3 SVG posters (#115). Save each and read source; only `launch-poster.svg` has an `<metadata>` export note with a base64 token:
```
echo '<token from launch-poster.svg>' | base64 -d   # -> adi-setup-override-7731
```
`welcome-poster.svg` is clean; `hackday-badge.svg` has only a troll comment. Aya #114 is the in-story pointer.

## Troll decodes (reassurance for NPCs)
- gym caption (#112) base64 -> "nice try detective, this is just my gym selfie caption...".
- `/resources/survey.txt` base64 -> "Q3 all-hands team-building survey (link expired...)".
- `/resources/` itself is a real exposed dir (robots points at it) but a dead end: press boilerplate + the joke survey, nothing that advances the chain.

## Security boundary with F2 (stays clean)
F1 ends at the discovery of `/internal-portal`. It never reveals F2's technique
(no cookies, keys, or admin trick). F1 runs its OWN signed login cookie with a
**server-only** key, so the F2 cookie-forging trick cannot be used to skip the F1
login, and F1 teaches nothing about F2's key. CTFd gates the F2 card behind S5.

## Verify after any rotation
```
cd firewall1 && python -m pytest -q      # 42 tests: all stages + trolls + negatives
```
