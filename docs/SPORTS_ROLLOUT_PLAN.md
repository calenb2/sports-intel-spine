# Sports Rollout Plan — V5 Data Spine Expansion
**Date:** July 5, 2026 · **Pattern:** each sport family copies tonight's proven soccer loop — one workflow (cron pull on GitHub's runners) + one distiller + one sport pack + Action endpoints + the 4-prompt eval battery. Nothing ships without passing its battery.

**Account bottom line:** you need exactly **one new free account** (CollegeFootballData email key). Kaggle keeps paying dividends (NBA fallback, CBB mirror, Olympics archives). One *paid* decision is deferred (Data Golf), gated on postmortem evidence.

---

## Rollout order (calendar-driven)

| # | Family | Why this order | Target |
|---|---|---|---|
| R1 | **MLB** | In season *right now* — corpus grows daily; easiest pipeline (free JSON, no key) | This week |
| R2 | **NFL + CFB** | Season opens September; pipeline testable immediately on 2025 data | Mid-July |
| R3 | **Tennis** + **club soccer extension** | Wimbledon now, US Open Aug; EPL/European leagues kick off mid-Aug | Late July |
| R4 | **NBA + CBB + NHL** | Tips/puck-drop October | September |
| R5 | **Golf decision + Olympics/majors Tier-1 packs** | No urgency (golf majors done for 2026; next Games LA 2028) | Anytime |

After the WC final (July 19): relax soccer cron 4×/day → daily.

---

## R1 — MLB (in season now)
- **Sources:** [MLB StatsAPI](https://statsapi.mlb.com/) (schedule/results/standings — free JSON, **no key**); [pybaseball](https://github.com/jldbc/pybaseball) → Baseball Savant Statcast (pitch-level 2015–present, aggregates for wOBA/xwOBA-style inputs — free, no account).
- **Account:** none.
- **Cadence:** nightly in season.
- **Distillate:** team profiles (rolling W-L, run diff/gm, wRC+-proxy offense index, starter/bullpen ERA-FIP proxies, park factor table static), Elo-style rating from results, last10.
- **Modeling map (V4 5-block):** Rating/RunEnv←Elo+park; Efficiency←Statcast aggregates; Context←Tier-3 browse (probable starters, lineups, weather); Market←browse.
- **Event archive (Tier-1):** World Series base rates — [Retrosheet](https://www.retrosheet.org) (free download, no account) deep history; one-time pull.
- **Risk:** Statcast rate limits on runners → pull daily deltas, not full history.

## R2 — NFL + CFB (one pack, two pipelines)
- **NFL sources:** [nflverse](https://nflverse.nflverse.com/) releases (verified live earlier) — PBP w/ EPA back to 1999, nightly in season, **no account**.
- **CFB sources:** [CollegeFootballData.com](https://collegefootballdata.com/key) — **free API key via email (YOUR ONE NEW ACCOUNT — create now, 2 minutes)**; [cfbfastR](https://cfbfastr.sportsdataverse.org/) ecosystem sits on top. Patreon tier only if we later want live/heavier pulls.
- **Cadence:** nightly in season (NFL Tue full refresh post-MNF), weekly off-season.
- **Distillate:** team profiles (EPA/play off/def, success rate, explosive rate, pace, Elo from results), QB-dependency flag (Tier-3 resolves status at ask-time).
- **Modeling map:** Efficiency←EPA aggregates (exactly V4's Block 3 inputs); Rating←Elo; drive overlay (file 09) unchanged — it's state-math, needs no feed.
- **Event archive:** Super Bowl base rates derivable from nflverse 1999+ plus one-time historical results pull; CFP/bowl base rates from CFBD.
- **Risk:** CFBD free-tier call caps → cache aggressively; nightly batch fits comfortably.

## R3 — Tennis + club-soccer extension
- **Tennis sources:** [TML-Database](https://github.com/Tennismylife/TML-Database) (live-updated ATP results, no account) primary for freshness; [Sackmann tennis_atp/wta](https://github.com/jeffsackmann/tennis_atp) (no account) for deep archive + WTA + serve/return aggregates. Staleness check in manifest — Sackmann update cadence is irregular (CC BY-NC-SA; personal use fine).
- **Distillate:** player profiles (surface-split Elo computed by our distiller from results, hold/break proxies, last10 by surface), tournament-week context.
- **Modeling map:** Rating←surface Elo; Serve/Return←aggregates; Context←Tier-3 (draws, fatigue, weather).
- **Event archive:** Slam base rates (favorite hold rates by round, five-set flip rates) from Sackmann history.
- **Club soccer:** [football-data.co.uk](https://www.football-data.co.uk/) CSVs (no account) — results + closing odds for top European leagues; drops straight into the existing soccer distiller with a league dimension. **Bonus: closing-odds history seeds the model-vs-market calibration layer.**
- **Risk:** tennis name-matching across sources (build alias table once).

## R4 — NBA + CBB + NHL
- **NBA sources:** [nba_api](https://pypi.org/project/nba_api/) → stats.nba.com (no account). **Known quirk: stats.nba.com intermittently blocks cloud-runner IPs** — plan A with retry/headers; plan B is a daily-updated Kaggle NBA mirror (you have Kaggle). Basketball-Reference stays browse-tier (respect ToS).
- **CBB sources:** [Barttorvik](https://barttorvik.com/) — free, no subscription, direct data endpoints (+[Kaggle mirror](https://www.kaggle.com/datasets/andrewsundberg/college-basketball-dataset)); adjusted efficiency/tempo = exactly V4's CBB inputs.
- **NHL sources:** [api-web.nhle.com](https://github.com/Zmalski/NHL-API-Reference) (free, no key — schedule/results/standings) + [MoneyPuck data page](https://moneypuck.com/data.htm) (free CSVs incl. **xG**, shots 2007–present; they ask for credit — SOURCES.csv already handles attribution).
- **Accounts:** none.
- **Cadence:** nightly in season.
- **Distillates:** NBA (net rating, pace, eFG%, Elo, rest flags), CBB (T-Rank-style adj. efficiency, tempo), NHL (xG for/against from MoneyPuck, special-teams rates, goalie GSAX proxy, Elo).
- **Event archives:** playoff/March Madness seed base rates (Barttorvik history), Stanley Cup base rates (MoneyPuck/NHL history).
- **Risk:** NBA runner-blocking (mitigated by Kaggle plan B); college name-matching (alias table).

## R5 — Golf decision + Olympics/majors packs
- **Golf:** [Data Golf API](https://datagolf.com/api-access) requires **paid Scratch Plus membership** (round-level SG across 22 tours, majors history 1983+; pricing on their site). **Recommendation: defer.** Golf runs browse-mode (V4-style) until your postmortem corpus shows golf volume/misses that justify the spend — that's the SIA-15 way to make a purchase decision. Free interim: OWGR + tour-site browsing at ask-time.
- **Olympics/majors Tier-1:** [Kaggle Olympedia archive](https://www.kaggle.com/datasets/josephcheng123456/olympic-historical-dataset-from-olympediaorg) (1896–2022; you have the account) + append Paris 2024 / Milan-Cortina 2026 — one-time static base-rate packs, no pipeline needed. Wimbledon/Masters-class archives derive from the tennis/golf history pulls above.

---

## Knowledge-slot budget
Current: 13 files. Adding 7 family packs (NFL+CFB, NBA+CBB, NHL, MLB, Tennis, Golf, Olympics/majors) = **20 exactly — at the cap.** Relief valve if ever needed: fold 06 (Run Summary) into 04 (Schema); they're procedurally adjacent. Each pack ships only when its sport's battery passes.

## Account checklist (complete state)
| Site | Status | Cost |
|---|---|---|
| Kaggle | ✅ have | free |
| GitHub | ✅ have (spine lives there) | free |
| CollegeFootballData | ⬜ **create now** — email → key at collegefootballdata.com/key | free |
| Data Golf | ⬜ deferred pending postmortem evidence | paid |
| The Odds API (optional, cross-sport odds history) | ⬜ only if the market layer wants deeper history later | free tier |
| Everything else (nflverse, MLB, NHL, MoneyPuck, Barttorvik, Sackmann, TML, football-data, Retrosheet) | no account exists or needed | free |

## Per-sport definition of done
1. Workflow green on manual dispatch + cron. 2. Distillate verified field-level vs source (like tonight's soccer check). 3. Sport pack written; weight profile declared. 4. Action endpoints added; vintage echo confirmed. 5. 4-prompt battery passed. 6. First postmortem row committed.
