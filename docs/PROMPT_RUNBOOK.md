# V5 Prompt Runbook
**v1.0 — July 5, 2026** · Master copy versioned in repo `docs/`. Four modes: daily, advanced, stress testing, back testing. Rule of thumb: the further down this document you go, the less often you should need it.

---

## 1. Daily use — zero ceremony

The system does everything automatically on casual prompts: Action call first, vintage echo in Block 2, confidence grade in Block 1, tripwires in the final block. If a covered sport ever answers *without* a vintage line or FEED_DOWN notice, that's drift — rerun the battery.

**Single game** (all you ever need):
```
Chiefs vs Bills
```
or with intent: `Who wins Portugal–Spain tomorrow?`

**Slate:**
```
MLB slate tonight, five-blocks on: Yankees @ Red Sox, Dodgers @ Giants, Astros @ Rangers
```

**Mixed sports:** just list them — SPORT is inferred per line.

**Live check (casual):**
```
Live check: Mexico vs England, 1-2, 67th minute. Win% and final score now?
```

**Shortcut phrases** (per 08_Sport_Shortcuts): "run the slate", "strict five-blocks", "four-block these fixtures", "grade last night's slate".

---

## 2. Advanced use

**Kalshi-style contract pricing:**
```
Price this contract vs your model: YES = "Brazil wins in 90 minutes AND total goals under 3.5", market 38¢.
```
Expect: legs parsed → joint probability → cheaper/fair/richer verdict only at confidence ≥ B− → settlement basis stated (90′ vs advancement).

**Model vs app/market tile:** paste or screenshot live percentages —
```
App shows MEX 22% / Draw 30% / ENG 48% — compare model vs app and explain the deltas.
```

**Advancement split (knockouts):**
```
Give both numbers: 90-minute H/D/A and advancement including ET/pens.
```

**Data vintage check:**
```
What's your data vintage for soccer? Call getSoccerDataVintage and report.
```

**Framework explanation (no prediction):**
```
Explain your framework for [sport]; no predictions.
```

**Weight-profile deviation:**
```
Model this as a must-win for the away side — deviate from the default profile and declare the change in Block 2.
```

---

## 3. Stress testing (validation mode — battery + pre-committed games per sport)

Standard per sport: 4-prompt battery once, then first 3 predictions graded **regardless of outcome** (pre-commit rule: choosing games after seeing results biases the corpus toward upsets and corrupts Brier stats). Log coverage on the tracker's Stress Tests sheet.

**S1 — Instrumented slate** (exercises Action, base rates, thin-data degradation, contract gate):
```
SPORT: <sport>
MODE: PREDICT_GAMES

GAMES:
- <marquee game 1>
- <marquee game 2>
- <deliberately thin-data matchup>

For Game 1 only, price: YES = "<favorite> wins AND <total condition>" — market <x>¢.
```
Pass: one profiles Action call for the whole slate; vintage echoed; confidence grades differ across games (thin-data game drops with SMALL_SAMPLE); no invented data for missing fields; sums ≈ 100%.

**S2 — Instrumented live check** (the provenance + log-line pattern):
```
MODE: REEVALUATE_IN_GAME
SPORT: <sport>

STATE:
- Game: <teams>
- Score: <current>
- Time: <segment/minute>
- Strength: <11v11 / 5v5 / etc.>

GAMES:
- <teams>

REQUIREMENTS FOR THIS RUN:
1. Before Block 1, print DATA PROVENANCE: every spine field and exact value
   received per team (with as-of date), separated from live-source facts.
2. After the Run Summaries, print one LIVE LOG LINE in CSV form:
   decision_id, timestamp, state, model probabilities, app %s if provided,
   confidence grade, top driver, active tripwire.
```
Pass: state echo; completed segments frozen; posterior coherent with score/time; provenance matches distillate field-for-field; source conflicts disclosed and priced (SIGNAL_SPLIT).

**S3 — Restraint test:** `Explain your framework for <sport>; no predictions.`
Pass = zero Action calls, zero probabilities, zero Run Summaries.

**S4 — Payload-echo audit** (verify it reads rather than invents):
```
For <team A> and <team B>, list every field you received from the Sports
Intel Spine and its exact value. No analysis.
```
Diff the answer against the repo distillate.

**S5 — Feed-failure drill** (optional; run when an Action error occurs naturally): pass = plain disclosure, FEED_DOWN cap ≤ B−, proceeds on browse + knowledge, never stalls.

---

## 4. Back testing / postmortems

**Single game:**
```
MODE: POST_GAME_REVIEW
Grade it: <teams> finished <final — note ET/pens if drawn at 90'>.
Pre-game prediction (logged): <score, probabilities, confidence>.
Live rows: <paste LIVE LOG LINEs if any>.
Note in-match events: <penalties, cards, key subs>.
```
Expect: outcome vs prediction with row Brier; miss classified per taxonomy (DATA_GAP / INJURY_INFO / TACTICAL_SURPRISE / VARIANCE / MODEL_ERROR / MARKET_RIGHT); one CSV row per model state (pre-game and live graded separately); update recommendation (none/watch/recalibrate).

**Batch:** `Grade last night's slate: <results list>. Emit POSTMORTEM ROWS only.`

**Version A/B protocol** (how the V4-vs-V5 experiment ran): run the identical slate through both versions, capture both Quick Views, log rows tagged by version, compare Brier after resolution. Same-day, same-fixtures pairing only.

**Corpus hygiene rules:**
- Never log a "pre-game" row after kickoff.
- Live rows carry the state timestamp, not the grading time.
- Grade pre-committed games regardless of outcome.
- The postmortem CSV is the data; the Stress Tests sheet is the coverage map.

---

## 5. Evolution log

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-07-05 | Initial set from V5 deployment day: instrumented live pattern (provenance + log line), postmortem format, pre-commit selection rule, contract gate phrasing. |

**Queued evolutions:**
- **V5.1 self-logging:** LIVE LOG LINE and POSTMORTEM ROWS stop being prompt requirements — the GPT writes rows to the repo itself; §3-S2 requirement 2 and §4 paste-backs retire.
- **Calibration-aware prompts:** once `getCalibrationStats` ships and N≥20/sport, add: "check your calibration history for this sport and cite corrections in Block 2."
- **App-tile layer:** still never tested with real numbers — first real win%-tile screenshot should be logged here as the S2-tile variant.
- Maintenance: any prompt pattern change bumps the version and gets one line here explaining why.
