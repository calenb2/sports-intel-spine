# 13 — Sport Pack: MLB (v1)

Applies to MLB regular season and postseason. Extends `01_Framework_Bible_v5` §3.6 (Baseball); overrides nothing outside MLB. Spine data refreshes nightly with same-day results — MLB is the freshest feed in the system.

## 1. Ontology (SIA-01)
- **Unit of analysis:** game (9-inning result; extras fold into final).
- **Phases:** starter innings (1–5/6), bullpen innings, high-leverage late states.
- **Roles:** starting pitcher (the single largest per-game variable), lineup core, bullpen tiers (high-leverage vs mop-up), platoon splits.
- **Outcome hierarchy:** plate appearance → inning → game → series → season.
- **Series context:** matchups repeat 2–4 nights; treat game predictions as conditionally dependent on bullpen usage the night before.

## 2. Weight profile (editable, SIA §8)
Regular season: Rating(Elo/Pythag) 30 · Market 25 · Starter matchup 25 · Context 10 · Form 10.
Postseason: shift +5 Market→Context (bullpen leverage, off-day patterns).
Starter matchup carries more weight than in any other sport pack — declare when a probable-starter change moves the number.

## 3. Spine payload (getMlbTeamProfiles — call once per run)
Per team: `gp, w, l, rs_pg, ra_pg, pythag, last10, elo, elo_rank` over a two-season Elo window; records/last10 from the current season. `as_of`/`data_through` at top — echo in Block 2.
**Not in the spine (Tier-3 browse at ask time):** probable starters, lineups, bullpen availability, park, weather, odds. The starter is why browse-mode still matters in MLB: spine gives the team base rate, the probable-starter search gives the single biggest daily adjustment.

## 4. Reference heuristics (glossary §5 + §8.5 apply)
- Home team wins ~54% at baseline; Elo gap adjusts from there. Pythag > actual W-L flags positive regression candidates (and vice versa).
- Typical run environment ~4.3–4.7 per side; park factors swing totals meaningfully (Coors up, pitcher parks down) — browse for park when totals matter.
- Runs cluster: middle innings (times-through-order penalty) and late bullpen-fatigue innings carry most scoring variance (Scoring-by-Period: End 3rd / End 6th / Final).
- One-game variance is enormous: 60% is a strong MLB favorite; treat 65%+ as rare and justify explicitly. Avoid extreme confidence in any single game.

## 5. Standing tripwires
- Probable starter scratched or changed → re-run; starter delta is the largest single-game swing.
- Bullpen back-to-back-to-back usage (3rd day) for either high-leverage arm → widen late-inning variance, note in Block 5.
- Weather: rain delay risk or wind out/in at total-sensitive parks → adjust total band, code WEATHER_UNK if unresolved.
- Lineup rest day for 2+ core bats → shift ~1–2% and drop confidence a notch, code LINEUP_NEWS.
- Doubleheader game 2 → rotation depth game; widen bands.

## 6. Data plumbing
- Staleness window in season: 2 days (`data_through` older → DATA_STALE, −1 grade).
- Statcast enrichment (xwOBA-class hitting/pitching quality) is queued as R1.2 — until then, quality metrics beyond run rates come from browsing per `03_Source_Registry` §7.
- World Series/postseason base rates: one-time Retrosheet pull queued; until then use browse-sourced base rates with a C source grade.
