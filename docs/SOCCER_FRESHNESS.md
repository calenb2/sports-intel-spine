# International soccer freshness

The refresh distinguishes the age of the newest result from evidence that an
expected match is missing. It keeps `data_through` unchanged during quiet periods;
`as_of` remains the processing date. The schedule continues checking four times
daily, including between international windows.

## November 6, 2026 incident

[Run 42154095060](https://github.com/calenb2/sports-intel-spine/actions/runs/42154095060)
downloaded 49,940 results and distilled 257 teams through October 6. The old
30-day age threshold failed at 31 days and skipped publication. A fresh download
on November 6 still contained 49,940 rows through October 6.

[FIFA's men's calendar](https://inside.fifa.com/tournament-organisation/international-match-calendars)
places the previous window on September 21–October 6 and the next on November
9–17. Those dates alone do **not** establish that the source is complete:
[SAFF scheduled its championship for November 4–17](https://saffederation.org/bangladesh-to-host-saff-championship-2026-from-november-4-17/),
and [AIFF confirms India's 3–2 win over Pakistan on November 5](https://www.the-aiff.com/article/india-defeat-pakistan-in-saff-championship-opener).
That result was absent from the downloaded CSV. FIFA's live feed still listed the
fixture as scheduled, illustrating why neither a window nor a single feed is
proof of completeness. The independently confirmed match is retained in the
reviewed calendar as a result witness.

The audit also found an older missing senior result: [Bahamas 2–3 U.S. Virgin
Islands on October 4](https://www.concacaf.com/competitions/nations-league/news/last-minute-victory-for-aruba-in-group-b).
[SAFF's results page](https://saffederation.org/match-results/) confirms both
November 5 openers, including Bhutan 0–1 Bangladesh. These three match facts are
recorded in `result_supplements.json`, with individual provenance. The primary
CSV stays unchanged; the distiller adds only absent results, skips identical
upstream results when the source catches up, and fails on score conflicts.

Two exact fixture corrections are also documented. [Mozambique's federation
identifies the September 30 Botswana match as U23](https://www.fmf.co.mz/index.php/news/details/1140),
so that incorrectly classified senior witness is excluded. [Sri Lanka's High
Commission's match schedule](https://www.facebook.com/SLinBangladesh/posts/1436402875345705/)
places Bangladesh–Sri Lanka on November 11, replacing FIFA's stale November 4
listing. The corrected November 5 SAFF opening date follows
[AIFF's October 30 squad announcement](https://www.the-aiff.com/article/naushad-moosa-names-28-player-squad-for-saff-championship-2026).
Corrections match the exact fixture ID, original date and teams; changed identity
or a conflicting completed status requires review.

## Publication policy

1. Fetch and validate required results into a temporary file before replacing the
   local copy. Both branch downloads failing is an error even if a cached CSV
   exists. Update the raw manifest's pull timestamp only after success.
2. Check CSV dates, scores and names. Merge the individually sourced supplements
   without changing the downloaded CSV. Reject future results, empty or malformed
   files, metadata mismatches, fewer than 200 profiled teams, and a lower row count
   or newest date than the last publication. Independently check primary row count
   and date so supplements cannot conceal source regression. Historical same-day doubleheaders
   remain valid and count as separate source rows.
3. Require a reviewed calendar covering the current UTC date. The initial calendar
   explicitly covers September 21–December 31, 2026. Outside that interval the
   guard fails; extending it requires checking FIFA **and regional tournaments**.
4. Between windows, require results through at least two days before the end of
   the last completed period. During a window, allow seven opening days, then
   require a result no older than seven days. Overlapping tournaments are checked
   independently, so an earlier regional start cannot be hidden by a later FIFA
   start. These are fallback stall checks, not match-completeness guarantees.
5. Query FIFA's public calendar from seven days before the **primary source's** newest result
   through today. Explicitly classify both teams as national, senior, men, outdoor
   football (`TeamType=1`, `AgeType=7`, `Gender=1`, `FootballType=0`). Observed query
   filters were silently ignored; filtering is performed locally. Competitions
   with exclusively out-of-scope classified teams are excluded. Completely unnamed
   scheduled bracket placeholders are counted but cannot witness a missing result.
   Other unclassifiable potential senior fixtures fail verification.
6. The feed caps responses at 500. Recursively split the requested interval until
   every response is complete. Validate bounds and IDs; fail on missing pagination
   metadata, malformed responses, HTTP failures, saturation at a single second,
   or a 128-request budget. Require at least one completed fixture overlapping
   the CSV so an empty/broken feed cannot certify a break. Refuse sources older
   than 180 days rather than issuing unbounded requests.
7. Compare fixture date and both normalized team names, ignoring home/away order.
   Accept either the explicitly supplied local or UTC match date to avoid rollover
   false alarms (no arbitrary date tolerance). Explicit aliases
   handle known provider naming differences. A missing fixture is `awaiting_results`
   for two complete UTC calendar days after its match date; it blocks at 00:00 UTC
   on day three. For the November 5 match this deadline is **November 8**, even
   though the FIFA window does not start until November 9. A recent different
   match cannot conceal an overdue fixture. Overdue scheduled or unknown-status
   fixtures also block pending verification; they are never silently treated as
   cancelled. Narrow reviewed fixture corrections apply before this comparison.
   Known official result witnesses apply even if FIFA omits the match.

`freshness_status.json` records state, unchanged data vintage, pending and overdue
fixtures, deadlines, calendar coverage and query URLs. It appears in the Actions
summary and as an artifact on either guard outcome. A failed pull/distill cannot
upload a stale prior success: the workflow clears the previous diagnostic first.
Only successful main-branch runs commit soccer raw files and distillates. Branch
dispatches can verify without committing or publishing.

## Maintenance and limitations

- **This is not a complete historical match audit.** The check covers the latest
  source date minus seven days onward. Older partial omissions, score errors,
  or fixtures missing from both feeds can escape detection. FIFA's classification,
  availability, and coverage are dependencies; non-FIFA internationals in the
  primary source may have no independent witness. A small regional competition
  can be missing even while another produces recent results.
- A cancelled/postponed/abandoned fixture, team alias mismatch, legitimate source
  correction that reduces row count, or provider schema change can stop publication.
  Investigate against the official competition/association report before changing
  policy. Do not broaden grace or delete an overdue witness just to make CI green.
- Keep `calendar.json` reviewed and extend its coverage **before January 1, 2027**,
  including confederation/regional tournaments and date changes. A calendar gap
  never disables the independent fixture check. Source URLs and `reviewed_on`
  must accompany updates; expiry deliberately requires human maintenance.
- The grace means recent incomplete results may publish with an explicit
  `awaiting_results` status and old `data_through`. Consumers must continue showing
  data vintage and applying the existing in-tournament confidence penalty.
- `shootouts.csv` remains optional and is not consumed by the current distiller.
  Elo remains a manual input with its existing independent vintage limitations.
- The live FIFA feed is verification evidence, not an alternate ratings dataset.
  Only individually reviewed match facts from the listed federation reports are
  supplements. No automatic scraping/import of arbitrary FIFA scores occurs.
  The guard retains minimal diagnostic fixture metadata and provenance.

## Verification and rollout

Run `python -m unittest discover -s tests -p 'test_*soccer*.py' -v`.
For a local live check, preserve the published meta before pulling/distilling, then
run `python scripts/soccer_freshness.py --previous-meta <saved-meta.json>`.
Use a disposable checkout for live pulls so generated distillates do not enter the
code PR. Unit CI is deterministic and read-only; live feed checks are separately
reported and can fail due to upstream evidence.

This change requires review/merge before production behavior changes. After an
authorized merge, verify a production run, its exact commit, status artifact and
committed data vintage. Supplements resolve the three verified omissions, not
future upstream stalls. New missing November fixtures must fail after grace, and
the fallback window guard must fail if the combined results stop advancing.
Do not close the incident solely because unit CI is green.
