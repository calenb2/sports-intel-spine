# 11 — Sport Pack: Soccer / World Cup 2026 (v1)

Applies to FIFA World Cup 2026 (48 teams, North America). Extends `01_Framework_Bible_v5` §3.4; overrides nothing outside this competition. Static snapshots below are dated — the Action's live versions always outrank them.

## 1. Ontology (SIA-01)
- **Unit of analysis:** match (90′ result) with a separate advancement layer for knockouts (ET + pens).
- **Phases:** established attack, defensive block, transition both ways, set pieces.
- **Roles:** creator density, target/runner profile, defensive anchor, GK distribution + shot-stopping tiers.
- **Outcome hierarchy:** chance → xG → goal → 90′ result → advancement → tournament progression.
- **Evaluation horizons:** pre-match; live; post-match (postmortem row); tournament (path-adjusted).

## 2. Weight profile (editable, SIA §8)
Group stage: Rating(Elo) 35 · Market 25 · xG/Chance creation 20 · Form/Schedule 10 · Context 10.
Knockouts: shift +5 from Form to Context (rest gaps, ET fatigue carryover, travel legs).
Declare any per-match deviation in Block 2 with one line.

## 3. Reference base rates (snapshot 2026-07-05 — refresh via getWorldCupBaseRates)
- All-time WC (1,054 games, 23 editions incl. 2026 to date): draw rate at FT ~22.5%, avg goals 2.83, ≤1 goal 26.6%, ≥4 goals 30.6%.
- Last 5 editions (346 games): draws ~23.1%, avg goals 2.65, ≤1 goal 27.7%, ≥4 goals 25.7%.
- Caveats: FT figures may fold in ET for knockout rows (treat draw rate as approximate); neutral venues dominate — "designated home" win rate (~43–46%) is NOT home advantage.

## 4. Elo snapshot (2026-07-05, WC-2026 field — live version in getSoccerTeamProfiles)
Spain 2165 (#1) · Argentina 2113 (#2) · France 2081 (#3) · England 2020 (#4) · Portugal 1984 (#5). Full 48-team table rides in the Action payload; use it, not memory.

## 5. Tournament tripwires (standing)
- Lineup shows 4+ rotations vs expected XI → re-run before kickoff.
- Confirmed GK change → re-run; shift per GK tier gap.
- Kickoff heat index >32°C or midday slot → nudge draw/under weight one notch; flag decay risk after 60′.
- Knockout reached via ET/pens in previous round → fatigue penalty on Form; check squad minutes in profiles.
- Market moves >4% on a side without public news → SIGNAL_SPLIT reason code; check for team news before trusting model divergence.

## 6. Contract settlement notes (Kalshi-style)
- Match markets typically settle on 90′ result (H/D/A); advancement markets settle on progression incl. ET/pens. NEVER price one basis with the other's probabilities.
- Quote both when relevant: "ARG 90′ win ~58%; ARG advance ~74%."
- Group-stage simultaneous final rounds: incentives can produce mutual-benefit scenarios — apply SIA-14 adversarial check before pricing draws.

## 7. Data plumbing
- `getSoccerTeamProfiles` once per run: 4-year window form + Elo for all teams (254 profiled).
- Staleness window in-tournament: 2 days. `data_through` older → confidence −1 grade, code DATA_STALE.
- Elo snapshot is pre-tournament-updated; large in-tournament rating moves lag — weight recent WC matches via form fields.
