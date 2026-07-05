# 00 — Index & Knowledge Map (V5)

Route every lookup to exactly one home. Never fetch via the Action what a knowledge file already holds.

| Need | File |
|---|---|
| Sport frameworks, blocks, models, weights | 01_Framework_Bible_v5 |
| Metric definitions, tempo heuristics, market concepts (incl. KALSHI_CONTRACT, TWO_WAY_VALUE_DUTCH) | 02_Metrics_and_Concepts_Glossary_v5 |
| Where to browse; source reliability grades; spine Action call policy | 03_Source_Registry_v5 |
| Prompt schema, modes (incl. POST_GAME_REVIEW), STATE fields | 04_Prompt_Schema_and_Usage_Cheat_Sheet_v5 |
| Output examples (incl. confidence layer + postmortem examples) | 05_Sample_Predictions_Playbook_v5 |
| Run Summary exact formats (+ confidence suffix) | 06_Run_Summary_Format_v5 |
| Logging, Brier/accuracy, miss taxonomy, recalibration triggers | 07_Evaluation_Protocol_v5 |
| Informal phrase → schema mapping | 08_Sport_Shortcuts_v5 |
| NFL/CFB live drive overlay | 09_Football_Live_Drive_Layer_v1 |
| SIA doctrine: 15 sections, analysis modes, decision brief | 10_SIA_Method_Condensed_v1 |
| World Cup 2026 ontology, weight profile, base rates, tripwires, settlement notes | 11_Sport_Pack_Soccer_WC2026_v1 |
| Confidence rubric, reason codes, evidence caps, shrinkage blend, ethics allowed-use | 12_Confidence_and_Governance_v1 |

**Requires the Action (rolling data — never in knowledge files):** current-season team profiles, live-ish form, data vintage. Soccer: `getSoccerTeamProfiles` (once per run), `getWorldCupBaseRates`, `getSoccerDataVintage`.

**Requires browsing (Tier-3 game state):** lineups, injuries, odds, weather, live scores — per 03 §2–8.

**Authority order:** Instructions → this index → 01 → 12 → 10 → sport packs → 02–09 → Action data → live web.

**Slot policy:** future sport packs group leagues by family (NFL+CFB; NBA+CBB; NHL; MLB; Tennis; Golf; Olympics/majors) to stay ≤20 files.
