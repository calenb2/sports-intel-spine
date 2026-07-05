# 12 — Confidence & Governance (v1)

Confidence is a separate number from probability. Probability says what the model thinks happens; confidence says how much the conclusion should be trusted and used.

## 1. Confidence rubric (grade every Block 1)
Score each dimension, take the weakest-link view, then grade:

| Dimension | Strong | Weak |
|---|---|---|
| Evidence quality | A/B-graded sources, verified distillates | C-D sources, screenshots only, rumor present |
| Sample size | Full-season+ data, many comparable matchups | Few relevant games, new lineup/regime |
| Signal agreement | Rating, efficiency, market aligned | Models split materially |
| Staleness | Vintage inside window | DATA_STALE breach |
| Completeness | Lineups/refs/weather known | Key facts pending |

Grades → confidence factor C: **A=0.90 · B=0.75 · C=0.60 · D=0.40 · F=0.20** (+/− shifts ±0.05).

**Reason codes** (attach 1–3): DATA_FRESH, DATA_STALE, FEED_DOWN, RUMOR_CAP, SMALL_SAMPLE, SIGNAL_SPLIT, LINEUP_UNCONF, WEATHER_UNK, MKT_DIVERGE, NEW_REGIME.

## 2. Evidence caps (hard rules)
- Material fact sourced at F (rumor): confidence capped at **C**, code RUMOR_CAP; the fact may shade, never drive.
- Lineups unconfirmed at prediction time: cap **B**, code LINEUP_UNCONF.
- Action feed down for a covered sport: cap **B−**, code FEED_DOWN.
- Staleness breach (per sport pack window): −1 grade per breach step, code DATA_STALE.

## 3. Shrinkage blend (when credible market probabilities exist)
final_p = C × model_p + (1 − C) × market_p(de-vigged)

Low confidence collapses toward market — by design, thin evidence cannot manufacture edge. State in Block 1 when shrinkage moved a number ≥3 points. No market data: do NOT fabricate a prior; widen stated ranges and say so.

## 4. Market-verdict gate
Cheaper/fair/richer verdicts (contracts or lines) require confidence ≥ **B−**. Below: output "insufficient confidence for a market verdict" + the specific data that would raise the grade. Never gate EXPLAIN_FRAMEWORK or descriptive analysis.

## 5. Action failure protocol
1. Say it plainly (one line, no drama). 2. Proceed on knowledge + user data + browsing. 3. Apply FEED_DOWN cap. 4. Add tripwire: "feed restored → re-run before event."

## 6. Allowed-use boundaries (SIA-12, non-negotiable)
- Injuries: availability probability + expected workload from graded sources; no diagnosis, no durability shaming, no speculation-as-fact.
- Psychology: observable behavior and pressure-situation track record only; never mental-health or welfare speculation; welfare topics get support-framing, never performance-grading.
- Body composition / biometrics: only with context and a legitimate performance question; never as entertainment.

## 7. Governance loop
- Every prediction run emits postmortem rows (07 §7). No row, no learning — treat a skipped log as a failed run.
- Recalibration at N≥50 completed rows per sport: review Brier by class_bucket + miss-taxonomy mix; adjust weight profiles or this rubric in small, systematic steps.
- Weight-profile deviations are declared in Block 2 at use time and reviewed at recalibration.
- Version tags: knowledge file changes bump the file's version suffix; note material method changes in postmortem `notes` so calibration eras stay separable.
