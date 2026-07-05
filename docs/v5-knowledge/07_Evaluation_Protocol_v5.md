# Evaluation Protocol (v5)

Purpose: define a light, repeatable way to log predictions from the Sports GPT, record actual outcomes, and compute simple quality metrics (accuracy, Brier score, and basic notes) across sports.

This is *not* a heavy research setup; it is a practical “how am I doing?” loop and a way to diagnose calibration and model-vs-market behavior.

---

## 1. Logging File: predictions_log.csv

Maintain a single CSV file, for example:

    predictions_log.csv

Each row = one game or match prediction.

### 1.1 Columns

Use this exact column order to match downstream scripts:

    date
    sport
    league
    game_id
    home_team
    away_team
    p_home
    p_draw
    p_away
    pred_home_score
    pred_away_score
    actual_home_score
    actual_away_score
    class_bucket
    p_home_mkt
    p_draw_mkt
    p_away_mkt
    overlay_tag
    notes

Field meanings:

- **date** – Game date in YYYY-MM-DD.

- **sport** – One of: NFL, CFB, NBA, CBB, NHL, SOCCER, TENNIS, BASEBALL, GOLF.

- **league** – Optional detail (e.g., “NFL”, “Premier League”, “ATP 500”, “MLB”, “PGA Tour”).

- **game_id** – A unique string like `DAL_LV_2025-11-20`, `EDM_WSH_2025-11-20`, `ALC_SIN_2025-11-20`, or `NYY_BOS_2025-11-20`.

- **home_team / away_team** – Team or player names:
  - For Tennis: treat Player A as “home_team” and Player B as “away_team”.
  - For Golf head-to-heads: treat Player A vs Player B similarly.
  - For Golf outrights: see note below (Section 3.3).

- **p_home** – Predicted win probability for the “home” side (0–1).

- **p_draw** – Predicted draw probability (0–1); use 0 for non-draw sports.

- **p_away** – Predicted win probability for the “away” side (0–1).

- **pred_home_score / pred_away_score** – Predicted final score line:
  - Football/Basketball/Hockey/Baseball: final points/goals/runs.
  - Soccer: final goals.
  - Tennis: number of sets won (e.g., 2 vs 1) or games if you choose that convention consistently.
  - Golf head-to-head: strokes (e.g., 69 vs 70) or score relative to par.

- **actual_home_score / actual_away_score** – Final score once the game or match is over, in the same units as the prediction.

- **class_bucket** – Classification of the *top* predicted outcome (largest of p_home, p_draw, p_away):
  - `CORE_FAVORITE` if top probability ≥ 0.60
  - `SMALL_LEAN` if 0.40 < top probability < 0.60
  - `LONGSHOT_LEG` if top probability ≤ 0.40 and the row represents a single-leg prediction with p < 0.20 (e.g., a draw you explicitly took as a longshot). For normal match rows, LONGSHOT_LEG will be rare; it is mainly for explicit longshot-side calls if you log them separately.

- **p_home_mkt / p_draw_mkt / p_away_mkt** – De-vigged **market** probabilities for home/draw/away at the time of entry, if available:
  - Use 0 when a leg is not applicable.
  - If you only have two-way odds, set p_draw_mkt = 0 and normalize p_home_mkt / p_away_mkt.

- **overlay_tag** – Optional text label describing any advanced overlay concept used:
  - Examples: `TWO_WAY_VALUE_DUTCH`, `ONE_WAY_VALUE`, `NO_VALUE_PAIR`, or `""` (blank).

- **notes** – Any quick notes (e.g., “OT”, “extra innings”, “Injury 1Q”, “red card 30'”, “rain delays”, “entry was live at Q4 5:12”, “entered via Kalshi contract X”).

Probabilities p_home + p_draw + p_away should sum to ~1.0 (or very close) for that row. Market probabilities may be empty or partial; they are only used when available.

---

## 2. Logging Workflow

### 2.1 Before games (prediction phase)

1. Use the Sports GPT as normal (single sport or mixed batch).

2. For each item, create one row in `predictions_log.csv`:

   - Record `date`, `sport`, `league`, `game_id`, `home_team`, `away_team`.
   - Copy the **model** probabilities from Block 1:
     - For two-outcome sports (NFL/CFB, NBA/CBB, NHL, TENNIS, BASEBALL, GOLF head-to-heads): p_home and p_away.
     - For SOCCER: p_home, p_draw, p_away.

   - Copy the predicted final score / setline into `pred_home_score` and `pred_away_score`.

   - If you also have market probabilities at entry:
     - Record them as `p_home_mkt`, `p_draw_mkt`, `p_away_mkt`, de-vigged as best you can.
     - Otherwise, leave them blank/zero.

   - Set `class_bucket` based on the top model probability:
     - ≥ 0.60 → CORE_FAVORITE
     - 0.40–0.60 → SMALL_LEAN
     - If you explicitly recorded a longshot leg (e.g., a Draw-only trade with p < 0.20), set class_bucket = LONGSHOT_LEG.

   - If you identified an overlay concept (e.g., TWO_WAY_VALUE_DUTCH for a soccer 3-way), set `overlay_tag` accordingly; otherwise leave blank.

3. Leave `actual_home_score` and `actual_away_score` blank for now.

You can either:

- Type rows directly into a spreadsheet with these columns, then export to CSV, or
- Maintain the CSV directly.

### 2.2 After games (result phase)

When results are available:

1. Open `predictions_log.csv`.

2. For each item:

   - Fill in `actual_home_score` and `actual_away_score`.
   - Optionally append details to `notes` (e.g., “OT”, “extra innings”, “retirement”, “weather delay”, “red card 30'”, “QB injury Q1”).

3. Save the CSV.

Now the file is ready for evaluation.

---

## 3. Metrics to Calculate

The companion Python script (or any equivalent) can compute metrics from `predictions_log.csv`.

### 3.1 Accuracy (winner)

- **Non-soccer, two-outcome sports**  
  (NFL, CFB, NBA, CBB, NHL, TENNIS, BASEBALL, GOLF head-to-heads):

  - Check whether the side with the higher win probability (p_home vs p_away) actually won the game/match.
  - If a league allows draws and one occurred (rare in this set), treat that game separately.

- **Soccer (three-outcome)**:

  - Compare the realized outcome (home, draw, away) to the leg with the highest model probability among (p_home, p_draw, p_away).
  - Accuracy = percentage of games where the highest-probability outcome matches reality.

It is recommended to compute accuracy **within each class_bucket** (CORE_FAVORITE vs SMALL_LEAN vs LONGSHOT_LEG) and by `sport`.

### 3.2 Brier Score (per game & average)

- **Two-outcome sports** (NFL, CFB, NBA, CBB, NHL, TENNIS, BASEBALL, GOLF head-to-head):

  - Let `p` = probability assigned to the actual winner (p_home or p_away, depending on who won).
  - Game-level Brier score = (1 − p)².
  - Average across games for mean Brier per sport and per class_bucket.

- **Soccer (three-outcome)**:

  - Use full 3-outcome Brier:
    - Probability vector: [p_home, p_draw, p_away].
    - Actual outcome vector: [1,0,0] for home win, [0,1,0] for draw, [0,0,1] for away win.
    - Brier = sum over outcomes of (p_i − actual_i)².
  - Average across games, again broken out by sport and class_bucket.

### 3.3 Golf outrights

Outrights with many possible winners do not fit neatly into this simple log format.

Options:

- Log only head-to-head or small “mini-field” events as GOLF head-to-head rows.
- Keep a separate sheet if you want detailed multi-outcome Brier evaluation for full fields.
- When in doubt, prioritize match-style events for this protocol.

### 3.4 Per-sport breakdown

- For each `sport`, compute:
  - Mean Brier score.
  - Accuracy.
  - Number of observations (N).

- Within each sport, also report by `class_bucket`:
  - CORE_FAVORITE: how sharp are big edges?
  - SMALL_LEAN: do we over/under-estimate coinflips?
  - LONGSHOT_LEG: how often are explicit longshot calls landing relative to p?

---

## 4. Model vs Market Diagnostics

When `p_home_mkt`, `p_draw_mkt`, and `p_away_mkt` are available, you can analyze **model vs market deltas**:

- For each leg `i` in {home, draw, away}:
  - Model probability: `p_i`
  - Market probability: `q_i` (from p_home_mkt/draw_mkt/away_mkt)
  - Delta: `Δ_i = p_i − q_i`

Aggregate statistics:

- Mean Δ per leg and per sport (e.g., are we systematically more bullish on underdogs?).
- Mean |Δ| (absolute deltas) to assess typical discrepancy.
- Relationship between Δ_i and realized outcomes (e.g., do positive-delta legs actually hit more than their market odds would suggest?).

Use these diagnostics to:

- Identify if the model is consistently “off-market” in a particular direction (e.g., always overrating trailing favorites in live states).
- Inform calibration tweaks (e.g., tempering extreme tails, especially in live comebacks).

---

## 5. Overlay Evaluation (e.g., TWO_WAY_VALUE_DUTCH)

For rows where `overlay_tag` is non-empty:

- Example tags: `TWO_WAY_VALUE_DUTCH`, `ONE_WAY_VALUE`, `NO_VALUE_PAIR`.

Use these labels to:

1. Track how often overlay situations occur by sport and league.
2. Evaluate whether these situations perform differently:
   - For TWO_WAY_VALUE_DUTCH:
     - In 3-way markets, how often does a non-draw outcome occur vs the draw?
     - Does the combined frequency of Home or Away outcomes align with or exceed the model’s expectations?
3. Check if your overlay identification criteria are too strict or too loose.

This overlay evaluation is **descriptive**, not prescriptive; it helps understand whether structural model-vs-market patterns (e.g., both non-draw legs showing positive deltas) correspond to actual outcomes over time.

---

## 6. Using the Evaluation Inside the Sports GPT

When you want analysis:

1. Export or open your `predictions_log.csv`.

2. Either:

   - Upload the CSV to a GPT session with tools (e.g., Code Interpreter) and run a small script, or  
   - Run your Python script locally and paste summary outputs back into the Sports GPT for interpretation.

Possible prompts to the Sports GPT using this protocol:

- “Here’s a summary of the last 50 predictions (sport, Brier, accuracy, class_bucket). Explain where the model seems overconfident or underconfident.”
- “Given this log, which sport looks most calibrated right now, and which needs recalibration?”
- “Compare calibration between soccer and tennis over the last 30 matches, especially for CORE_FAVORITE vs SMALL_LEAN buckets.”
- “Look at model vs market deltas for soccer draws. Are we systematically more or less bullish on draws than the market?”

The Sports GPT should:

- Treat this evaluation protocol as the ground truth for how to think about performance.
- Propose **small, systematic tweaks** (such as slightly moderating very high probabilities or adjusting live comeback aggressiveness) rather than overfitting to one streak of results.
- Keep recommendations at the level of **calibration and explanation**, not staking or trading strategies.

---


## 7. V5 Postmortem Loop (repo-wired)

The logging home is now `postmortem/postmortem_log.csv` in the `sports-intel-spine` repo. Everything in sections 1–6 still applies; the CSV gains V5 columns and a commit ritual.

**Column mapping (v2 → repo)**: date→date · sport→sport · game_id→decision_id · home/away teams→event · p_home/p_draw/p_away + pred scores→prediction · p_*_mkt→market_prob · class_bucket & overlay_tag→notes. 

**New V5 columns**: `confidence_grade` (Block 1 grade at prediction time) · `as_of_data` (distillate vintage used) · `miss_reason` (taxonomy below) · `model_update_needed` (none/watch/recalibrate).

**Miss taxonomy (choose primary):**
- DATA_GAP — material fact unavailable at prediction time
- INJURY_INFO — availability/workload info wrong or late
- TACTICAL_SURPRISE — lineup/shape/approach outside scouted range
- VARIANCE — outcome within stated distribution; no error
- MODEL_ERROR — systematic mis-rating (weights, priors, blend)
- MARKET_RIGHT — market divergence resolved in market's favor
- OTHER — describe in notes

**Ritual**: every PREDICT_GAMES run logs rows before the event; POST_GAME_REVIEW completes them after. Commit at least weekly in-season.

**Recalibration trigger**: at N≥50 completed rows per sport, review Brier by class_bucket and miss-taxonomy mix; adjust sport weight profiles or confidence rubric — small, systematic tweaks only, never single-streak overfits.

_End of Evaluation Protocol v5_
