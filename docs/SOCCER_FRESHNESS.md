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
listing. On November 8 a third correction moved Sri Lanka–Bhutan from FIFA's
provisional November 7 to the [published schedule's November 8](https://www.thedailystar.net/sports/football/news/saff-championship-2026-all-you-need-know-4315616),
so its deadline is November 11 00:00 UTC alongside Maldives–Pakistan. The corrected November 5 SAFF opening date follows
[AIFF's October 30 squad announcement](https://www.the-aiff.com/article/naushad-moosa-names-28-player-squad-for-saff-championship-2026).
Corrections match the exact fixture ID, original date and teams; changed identity
or a conflicting completed status requires review.

## November 8, 2026 incident

[Run 42436558372](https://github.com/calenb2/sports-intel-spine/actions/runs/42436558372)
pulled and distilled normally, then the independent FIFA check died with
`http.client.IncompleteRead(305950 bytes read)`: the API closed a chunked
response early on one of the ~50 split-interval pages. `get_json()` had no
retry, `IncompleteRead` is an `HTTPException` (not in the handler's list), so the
exception escaped before any status file was written, and the artifact step
accepted "no files found". Publication was correctly skipped; the diagnostic gap
was the defect. The same truncation recurred on 1 of 6 local replays on
November 8 (765,457 bytes read) and was absorbed by a single retry.

Repair (this document's version): every request goes through
`scripts/soccer_transport.py`, every stage writes a diagnostic on failure, and
the workflow treats a missing diagnostic as an error. Policy semantics (grace,
deadlines, regression checks, supplements, corrections) are unchanged.

### Transport bounds

| Bound | Value | Where |
|---|---|---|
| Attempts per URL | 4 | `MAX_ATTEMPTS_PER_URL` |
| Backoff | 1 s, x2, cap 20 s, +/-25 % jitter | `_backoff` |
| `Retry-After` | honoured (seconds or HTTP-date), cap 60 s | `_retry_after_seconds` |
| Retried | truncated/short/empty bodies, timeouts, resets, DNS/socket errors, HTTP 408/425/429/500/502/503/504 | `_classify` |
| Not retried | other 4xx, TLS verification failures, complete-but-invalid JSON | `_classify`, `InvalidResponse` |
| FIFA logical queries | 128 interval splits | `FIFA_MAX_QUERIES` |
| FIFA physical requests | 192 (128 queries + 64 retries), 600 s wall clock | `FIFA_MAX_REQUESTS`, `FIFA_MAX_ELAPSED_S` |
| Pull physical requests | 16 (2 files x 2 branches x 4 attempts), 420 s | `PULL_MAX_REQUESTS`, `PULL_MAX_ELAPSED_S` |
| Publish readback | 8 requests, 90 s | `soccer_publish_verify.verify` |
| Workflow backstop | job 25 min; steps: install 5, pull 9, distill 3, verify 12, publish 4, publish-verify 4 | `refresh-soccer.yml` `timeout-minutes` |

The physical budget is checked before each request, so nested retries cannot
multiply past it; running out of budget is a `TransportError(category="budget")`.
The elapsed budget is a true end-to-end deadline, not a per-connect timeout: the
socket timeout is clamped to whatever remains (sub-second included, no floor),
bodies are read in 64 KiB chunks with the deadline re-checked between chunks,
and a stream still running when the deadline passes fails as
`category="budget"` / `deadline_exceeded` without retry. A read that completes
late but inside the deadline is accepted; the next request simply gets the
remaining time. A retry whose backoff would cross the deadline is refused
rather than slept through. The workflow `timeout-minutes` values exist only as
a backstop; if one fires, the run's init record (below) is what gets uploaded.
A later page that fails after earlier pages succeeded raises; `fetch_fixtures`
never returns a partial collection, and the attempted query list is preserved
in the diagnostic because the caller owns the history list.

### Diagnostics contract

`distillates/soccer/freshness_status.json` (schema 2) is **run-scoped**. The
first step after checkout (system `python3`, before any dependency install)
runs `soccer_diagnostics.py --init`, which replaces the committed file (the
previous successful run's) with this run's `state: in_progress` record carrying
`run_id`, `commit`, `started_at`, `last_good` and a `superseded_record` note.
From that point the artifact can never be a stale success, even if `pip
install` fails. Later steps (`--if-missing`, `--annotate`, publish verification)
accept an existing record as current only if it parses, has `schema_version: 2`
and carries this run's `GITHUB_RUN_ID`; anything else is replaced and noted
under `rejected_record` (`malformed` / `schema_mismatch` / `wrong_run`).

The file is then overwritten by whichever stage fails — `pull`, `distill`,
`verify` — and by `verify` on success. Fields:
`stage`, `state`, `publish_allowed`, `error_category`
(`transport:<transport|http_permanent|budget|tls>`, `invalid_response`,
`validation`, `schema`, `io`, `unexpected:<Type>`, `diagnostic_gap`),
`errors`, `traceback` (tail), `started_at`/`finished_at`, `commit`, `run_id`,
`run_attempt`, `last_good` (previous published vintage), `source_data_through`,
`source_rows_total`, `fixture_queries`, `fixture_query_count`, and `transport`
(physical request count, elapsed, per-attempt history with sanitized URLs). A
`pull` failure is typed: `error_category` is `transport:<category>` of the last
branch tried, with `failed_url`, `failed_url_attempts` and a per-branch
`download_failures` list (`http_permanent`, `tls`, `budget`, `transport`); only
a complete download that fails CSV validation is `validation`. The workflow
writes a `diagnostic_gap` record if no stage produced one and uploads with
`if-no-files-found: error`. `verify` also
checks that `team_profiles.json` and `wc_base_rates.json` agree with `meta.json`
(as_of, data_through, team count, W/D/L totals) and that no distillate contains
NaN/Infinity.

### Publication verification

On `main`, after the commit/push step — whatever its outcome —
`soccer_publish_verify.py` records what actually happened, never what was
intended: it reads the remote `main` head with `git ls-remote`, and reads the
committed `meta.json` and `team_profiles.json` back from the immutable
`raw.githubusercontent.com/<repo>/<sha>/…` URL through the bounded transport.
`published` is `true` only when the remote head is (or contains) this run's
commit **and** the readback is byte-identical to the local files; `"unchanged"`
when nothing was committed and the remote base's `meta.json` reads back equal
to the previously published meta; `false` when the push did not land and the
remote still serves the base commit (with `last_good_verified` set only if the
base meta read back equal — "last-good remains published" is an observation,
not an assumption); and `"unknown"` whenever the remote head is unreadable,
readback mismatches, or the remote moved to a commit whose relationship to
ours cannot be established. The step exits non-zero if the push step reported
success but publication could not be confirmed. The result is merged into the
run's status record under `publish` / `published` / `last_good_verified`.

### Primary-source cadence and licensing (verified 2026-11-08)

- `martj42/international_results` states **no update schedule**; results are
  added by community pull requests. On November 8 the CSV still ended at
  2026-10-06 (49,940 rows). This workflow polls 4x daily and enforces a two-day
  missing-result deadline, so **the primary source alone cannot satisfy the
  completeness policy during a window**; `awaiting_results` -> `blocked` after
  grace is the designed, truthful outcome, not a bug. The three supplements
  cover verified omissions only.
- The repository `LICENSE` file is **CC0 1.0 Universal**. `MANIFEST.json` and
  `SOURCES.csv` previously said CC BY 4.0 and are corrected. CC0 covers the
  martj42 rows only; it confers nothing on FIFA or any other provider's data.
- Candidate current-results feeds (none adopted; each needs an account, a key,
  and in two cases a rights decision — outside this repair's authorization):
  API-Football (free 100 req/day, all competitions on all plans per its pricing
  page; terms page not retrievable on 2026-11-08, publication rights unverified),
  Sportmonks (caching inside a product allowed, raw-feed redistribution needs
  written approval; SAFF men's coverage unconfirmed), football-data.org (no SAFF
  or friendlies listed), OpenFootball internationals (martj42 mirror, not
  independent). FIFA stays a witness: it listed Sri Lanka-Bhutan on the
  September provisional date (Nov 7) when the published schedule says Nov 8.

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
   metadata, malformed responses, exhausted transport retries/budgets (see
   "Transport bounds"), saturation at a single second, or the 128-query budget. Require at least one completed fixture overlapping
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
fixtures, deadlines, calendar coverage, query URLs and the transport/diagnostic
fields above. It appears in the Actions summary and as an artifact on every
outcome; a failed pull/distill writes its own stage record rather than leaving
nothing, and the workflow clears the previous run's file first so a stale
success can never be uploaded.
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
