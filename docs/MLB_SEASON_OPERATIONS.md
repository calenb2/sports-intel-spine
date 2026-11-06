# MLB season-aware refresh and restart record

## Change status

Prepared 2026-11-01 for review. A branch/PR is not a deployed fix. The production
schedule changes only after this change is reviewed and merged into `main`.

The old `R,P` schedule filter omitted postseason round codes. The distiller now
requests `R,F,D,L,W` for the full calendar year, and the UTC-year rollover retains
the most recent completed season until the new season has scored final games.
Spring-training (`S`) results remain excluded from ratings.

## Verified 2027 dates and restart plan

Verified against MLB's season metadata **and actual schedule** on 2026-11-01 UTC:

| Milestone | MLB calendar date | Scheduled check | Dallas local time |
|---|---|---|---|
| Spring training starts (monitor only) | 2027-02-19 | 2027-02-19 09:00 UTC | 03:00 CST |
| Regular season starts (ratings resume as finals arrive) | 2027-03-25 | 2027-03-25 09:00 UTC | 04:00 CDT |

These are MLB `officialDate` calendar dates, **not first-pitch timestamps**.
The opening-date morning check may precede all games. The following day's
09:00 UTC check normally captures opening-date finals. GitHub scheduled jobs can
run late; no exact execution-time guarantee is made.

Sources (requeried every day, so changed dates automatically supersede this snapshot):

- https://statsapi.mlb.com/api/v1/seasons/2027?sportId=1
- https://statsapi.mlb.com/api/v1/schedule?sportId=1&season=2027&gameTypes=R,F,D,L,W,S
- https://statsapi.mlb.com/api/v1/seasons/2026?sportId=1
- https://statsapi.mlb.com/api/v1/schedule?sportId=1&season=2026&gameTypes=R,F,D,L,W,S

MLB metadata lists the 2026 season end as October 31 and offseason beginning
November 1. The verified last scored final is October 28. Its calendar age is
not treated as an outage during a verified offseason.

## What keeps running

Do **not** disable the workflow in winter: the daily 09:00 UTC job is the automatic
restart mechanism. It fetches official seasons and schedules, validates results,
and publishes `distillates/mlb/season_status.json` with phase, evidence URLs,
checked-at UTC, latest final, future spring/regular dates, next check and restart.
The same record is written to the GitHub Actions step summary. The dated record
is committed alongside successful distillates, preserving a GitHub history.

No hard-coded date automatically declares a season healthy. Season metadata
defines the normal active window (actual scheduled opener takes precedence);
outstanding schedule games extend it for late postseason play. A verified
four-win World Series clinch with no outstanding games permits an early offseason.
During the active season a lag greater than 3 days fails, with
an opening-day grace through day 3 while the first finals become available.
The distillate's latest result date must always match MLB's latest scored final,
including during winter, so omitting postseason results cannot silently pass.

A valid future response with unpublished dates records `null` / `not published`
and rechecks the next day; it never invents a restart date. HTTP, JSON, malformed
metadata, missing required history and stale active-season data fail the job and
skip publication. They are **not** reclassified as offseason. Failures preserve
the previously committed data; its prior timestamp must not be mistaken for a
fresh successful check. No credentials, grants, or account settings are added.

## Validation and closure

Run `python -m unittest discover -s tests -p 'test_*mlb*.py' -v`.
Live read-only smoke: `python scripts/distill_mlb.py && python scripts/mlb_season.py`.
Unit tests use fixtures, never network calls. PR CI is read-only and does not
publish distillates. The existing scheduled workflow's publication remains
restricted to `distillates/mlb/`.

Before closure: merge only with approval, observe a successful production run,
verify the committed `season_status.json` has an up-to-date check timestamp and
the expected dates, and confirm postseason finals in `meta.json`. January must
retain the prior completed season; spring-training scores must not enter ratings;
the first regular-season finals must switch profiles to the new season.

Rollback: revert the reviewed change. Do not bypass the freshness guard to make
a run green. An API or schema failure should remain visible for investigation.

## Source / license provenance

Only MLB StatsAPI public schedule/season data is used. Source responses carry:
“Copyright 2026 MLB Advanced Media, L.P.” and link the provider's terms at
http://gdx.mlb.com/components/copyright.txt . This change does not claim broader
redistribution rights. Runtime output records sources and UTC retrieval dates;
`docs/mlb-restart-verification-2026-11-01.json` is the compact dated verification
manifest, rather than a checked-in bulk schedule.
