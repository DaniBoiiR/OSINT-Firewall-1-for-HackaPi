# Firewall 1 - Challenge Documentation (pentest brief)
Aurelian Dynamics "Aurelian Pulse" - OSINT / information-disclosure recon.

Firewall 1 is the **reconnaissance phase** of the engagement. Players do not
exploit code here; they harvest information a company has carelessly exposed, and
each piece of recovered intel (the "loot") is what they report. The final piece
is the location of the hidden staff portal, which is where **Firewall 2**
(exploitation) begins. No CTF flag strings are used; answers are the real intel.

Solvable with a browser and the offline LLM only. No local tools (exiftool,
terminal) are required: the LLM handles base64, and SVG source is read in the
browser.

---

## Stage 1 - Insider identification
- **Class:** OSINT profiling / correlation of public information.
- **Exposure:** an employee overshares about causing an incident; her staff ID is public on her profile.
- **Recon path:** read feed -> correlate the panicking intern with the "who skipped the auth gate" callout -> she is not in suggestions, so Search -> open profile.
- **Loot:** Staff ID `ADI-2291`.
- **Real-world lesson:** individually harmless posts become identifying when correlated.

## Stage 2 - Forced browsing / unlisted content
- **Class:** Broken access control (information disclosure via unlisted resource); object enumeration.
- **Exposure:** a post removed from listings is still served by direct URL. Deletions leave guessable gaps in the ID sequence.
- **Recon path:** notice skipped post numbers -> request them directly -> sort real content from decoy "removed" pages.
- **Loot:** SSO migration codename `SKYLINE` (and a pointer to the resources folder).
- **Lesson:** "unlisted" and "deleted from the UI" are not access controls.

## Stage 3 - Exposed directory
- **Class:** Security misconfiguration (sensitive files in a world-readable path; robots.txt as a signpost).
- **Exposure:** `robots.txt` advertises `/resources/`; a maintenance note was left there.
- **Recon path:** robots.txt -> `/resources/` listing -> read the note.
- **Loot:** staging host `portal-stg.adi.internal` (plaintext).
- **Lesson:** robots.txt is a discovery hint, not protection; do not leave working files in public paths.

## Stage 4 - Sensitive data exposure (Firewall 2 pivot)
- **Class:** Sensitive data exposure; "encoding is not encryption."
- **Exposure:** the production portal path is stored base64-encoded in the same note, alongside a decoy base64 blob and a plaintext build string.
- **Recon path:** identify the encoded line -> decode base64 (via the LLM) -> ignore the decoy blob.
- **Loot:** portal path `/internal-portal` (+ build `adi-portal@2.3.1`). **This unlocks Firewall 2.**
- **Lesson:** base64 is reversible; it hides nothing.

## Stage 5 - SVG source inspection (bonus, hardest)
- **Class:** Metadata / artifact disclosure in a vector asset.
- **Exposure:** a poster SVG ships with an "export note" containing a base64 setup code in `<metadata>`. Two other posters are decoys (one clean, one with only a troll comment).
- **Recon path:** recognise SVG is text -> save and open source -> find the right poster -> decode the base64.
- **Loot:** setup code `adi-setup-override-7731`.
- **Lesson:** exported assets carry hidden layers/metadata; vector files are code, not flat images.

---

## Deliberate time-sinks (anti-rush design)
- Two base64 decoys (a gym caption, a survey file) that decode to jokes: punishes "decode everything."
- Two false-loot values (`ADI-0001`, `/employee-dashboard`) that look right and are rejected by the scoreboard.
- Multiple "removed" troll pages among the post-ID gaps: only one gap holds real intel.

## Hand-off to Firewall 2
Firewall 1 ends at the discovery of `/internal-portal`. It never reveals how F2
is exploited (no cookies, keys, or admin technique). CTFd gates the F2 challenge
behind the Stage 4 answer. Recon feeds exploitation; the boundaries stay clean.

## Progressive gating
S1 -> S2 -> S3 -> S4 -> Firewall 2, enforced as CTFd prerequisites. S5 is an
independent bonus with no dependents.
