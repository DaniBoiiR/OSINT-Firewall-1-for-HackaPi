# Firewall 1 - Challenge Documentation (pentest brief)
Aurelian Dynamics "Aurelian Pulse" - OSINT / information-disclosure recon.

Firewall 1 is the **reconnaissance phase** of the engagement. Players do not
exploit code here; they harvest information a company has carelessly exposed,
log in as the insider using what she overshares, and follow her private trail to
the hidden staff portal, which is where **Firewall 2** (exploitation) begins.
No CTF flag strings are used; answers are the real intel.

Every stage's loot is the literal key to the next, so the chain cannot be
short-circuited: **staff ID -> login username; password -> session; codename ->
folder name; removed-posts log -> which "deleted" post is still live (#106);
base64 inside /post/106 -> portal path -> F2's door.**

Solvable with a browser and the offline LLM only. No local tools (exiftool,
terminal) are required: the LLM handles base64, and SVG source is read in the
browser.

---

## Stage 1 - Insider identification
- **Class:** OSINT profiling / correlation of public information.
- **Exposure:** an employee overshares about causing an incident; her staff ID is public on her profile.
- **Recon path:** read feed -> correlate the panicking intern with the "who skipped the auth gate" callout -> she is not in suggestions, so Search -> open profile.
- **Loot:** Staff ID `ADI-2291`.
- **Key to next:** it is her login **username**.
- **Lesson:** individually harmless posts become identifying when correlated.

## Stage 2 - Credential profiling
- **Class:** Weak/guessable password built from personal information; auth hygiene.
- **Exposure:** she brags her password is "all my favourite things" and scatters those things across her posts (cat name, drink, birthday). A legacy "password hint" feature on the login page discloses the hint when a valid staff ID is entered with the wrong password. Username enumeration: an unknown ID is rejected differently from a known one.
- **Recon path:** find the three favourites -> assemble the password -> log in. (Two decoys: sticky-note kiosk creds that work but are useless, and an expired old password.)
- **Loot:** password `mochimatcha2004`.
- **Key to next:** it logs you in as Aya (the session).
- **Lesson:** never base a password on personal details you post publicly; never disclose password hints; distinct auth errors enable enumeration.

## Stage 3 - Private data disclosure (post-authentication)
- **Class:** Broken access control / sensitive data behind a weak login.
- **Exposure:** once logged in as Aya, her inbox (DMs) reveals the internal migration codename and that she relocated the real notes into a project folder named after it. None of this is public.
- **Recon path:** log in -> Messages -> read the argument with Theo.
- **Loot:** migration codename `SKYLINE`.
- **Key to next:** it is the **project folder name** (`/projects/skyline/`).
- **Lesson:** a login is not a vault; weak auth exposes everything behind it.

## Stage 4 - "Deleted" is not deleted
- **Class:** Broken access control / data remnants (unlisting hides from the UI but the object is still served).
- **Exposure:** `robots.txt` advertises `/projects/`; its index is disabled (no enumeration), but the folder name is known from S3. Inside `/projects/skyline/` is `removed-posts.log` - Aya's export of her "removed" posts, each with a reason and a status. The trolls are genuinely deleted; one post (#106) is only *unlisted* and is still served by direct URL.
- **Recon path:** robots.txt -> `/projects/` (listing disabled) -> `/projects/skyline/` -> read `removed-posts.log` -> spot the entry flagged `STILL LIVE at /post/106`.
- **Loot:** `106` (the post that is still reachable).
- **Key to next:** that post is where S5 lives.
- **Lesson:** removing a post from a listing is not deletion; the object is still retrievable. Reinforced by Theo's public DM ("your deleted post still opens").

## Stage 5 - Sensitive data exposure (Firewall 2 pivot)
- **Class:** Sensitive data exposure; "encoding is not encryption"; authorization-scoped content.
- **Exposure:** `/post/106`, opened in Aya's authenticated session, reveals the relocated production portal path base64-encoded in the post body. The same URL shows only harmless panic text to anyone who is not Aya, so the secret cannot leak ahead of the chain.
- **Recon path:** open `/post/106` as Aya -> decode the base64 line (via the LLM).
- **Loot:** portal path `/internal-portal`. **This unlocks Firewall 2.**
- **Lesson:** base64 is reversible; and the same URL can expose more to a privileged session - fetch it with the right identity.

## Stage 6 - SVG source inspection (bonus, hardest)
- **Class:** Metadata / artifact disclosure in a vector asset.
- **Exposure:** a poster SVG ships with an "export note" containing a base64 setup code in `<metadata>`. Two other posters are decoys (one clean, one with only a troll comment).
- **Recon path:** recognise SVG is text -> save and open source -> find the right poster -> decode the base64.
- **Loot:** setup code `adi-setup-override-7731`.
- **Lesson:** exported assets carry hidden layers/metadata; vector files are code, not flat images.

---

## Deliberate time-sinks (anti-rush design)
- **Troll tools / decode traps:** two base64 decoys (a gym caption, a survey file) that decode to jokes, and a whole decoy exposed directory (`/resources/`) that robots.txt points at but leads nowhere. Lesson: not every tool-use pays off.
- **Decoy credentials:** sticky-note kiosk creds (`ADI-1001`/`Welcome123!`) that log in but to a dead-end account; an expired old password (`sunshine2004`).
- **False loot:** `ADI-0001` and `/employee-dashboard` look right and are rejected by the scoreboard.
- **Troll "removed" pages:** several post-ID gaps are empty taunts; #106 opens but only confirms the notes moved behind the login.

## Hand-off to Firewall 2
Firewall 1 ends at the discovery of `/internal-portal`. It never reveals how F2
is exploited (no cookies, keys, or admin technique). F1 runs its own signed login
cookie with a server-only key, independent of F2, so F2's cookie trick cannot
skip the F1 login. CTFd gates the F2 challenge behind the Stage 5 answer. Recon
feeds exploitation; the boundaries stay clean.

## Progressive gating
S1 -> S2 -> S3 -> S4 -> S5 -> Firewall 2, enforced as CTFd prerequisites. S6 is
an independent bonus with no dependents.
