# Firewall 1 - ORGANIZERS ONLY - Loot & Full Solve
Keep OFF the player network and out of the Go-Bag. Not needed at runtime.

Base (dev): http://127.0.0.1:5000 (replace with the event host/port).

## Loot to load into CTFd (defaults; rotate via .env)
| Stage | Submit string | Gate |
|---|---|---|
| S1 | `ADI-2291` | unlocks S2 |
| S2 | `SKYLINE` | unlocks S3 |
| S3 | `portal-stg.adi.internal` | unlocks S4 |
| S4 | `/internal-portal` | **unlocks Firewall 2** |
| S5 | `adi-setup-override-7731` | bonus, no gate |

Set CTFd answer matching to case-insensitive. S4 is the token that opens the F2
challenge card (set F2's prerequisite to S4). S5 has no dependents.

## Decoys the scoreboard must REJECT (do not add these as accepted answers)
- `ADI-0001` (CEO post #101) - fake staff ID.
- `/employee-dashboard` (Theo post #116) - fake portal path.

## Full solve
**S1:** Aya (@a.nocari) is not in "Who to follow". Feed posts #104/#106-trail and Theo's #107 point at her. Search "portal"/"intern" -> her profile -> Staff ID `ADI-2291`.

**S2:** Feed skips post numbers (admin deletions). Theo #109 says a "deleted" post is still reachable. Enumerate `/post/<id>` over the gaps:
- #103, #111, #113 -> troll "removed" pages (ragebait).
- #106 -> the real hidden post: codename `SKYLINE`, points to `/resources`.

**S3:** `/robots.txt` disallows `/resources/`. Open `/resources/` -> `portal-migration-notes.txt` leaks staging host `portal-stg.adi.internal` (plaintext).

**S4:** Same note hides the portal path in base64:
```
echo 'L2ludGVybmFsLXBvcnRhbA==' | base64 -d      # -> /internal-portal
```
The note also has a troll base64 ("survey...") and plaintext build `adi-portal@2.3.1`. Submitting `/internal-portal` unlocks F2.

**S5 (bonus):** Mira posts 3 SVG posters (#115). Save each and read source; only `launch-poster.svg` has an `<metadata>` export note with a base64 token:
```
echo '<token from launch-poster.svg>' | base64 -d   # -> adi-setup-override-7731
```
`welcome-poster.svg` is clean; `hackday-badge.svg` has only a troll comment. Aya #114 is the in-story pointer.

## Troll decodes (reassurance for NPCs)
- gym caption (#112) base64 -> "hey nice try, this is just a gym selfie caption, wrong clue".
- `/resources/survey.txt` base64 -> "Q3 all-hands team-building survey (link expired...)".

## Verify after any flag rotation
```
cd firewall1 && python -m pytest -q      # 27 tests: all stages + trolls + negatives
```
