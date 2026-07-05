# Prompt Schema & Usage Cheat Sheet (v5)

This file defines how the Sports GPT should interpret prompts and normalize them into a consistent internal schema.

---

## 1. Command Schema

Internally, the assistant should normalize inputs into this structure:

    SPORT: <NFL | CFB | NBA | CBB | NHL | SOCCER | TENNIS | BASEBALL | GOLF>   # optional but preferred
    FORMAT: <FOUR_BLOCK | FIVE_BLOCK>                                          # optional; defaults per sport
    DATE: YYYY-MM-DD                                                           # optional
    MODE: <PREDICT_GAMES | EXPLAIN_FRAMEWORK | REEVALUATE_IN_GAME>             # optional

    STATE:                                                                     # optional; used in REEVALUATE_IN_GAME
    - Game: <Match label, e.g., Team A vs Team B, Player A vs Player B>
    - Score: <current_score or sets>
    - Time: <time remaining / current inning / current set / match minute>
    - Strength: <e.g., 5v5, 11v11, power play, etc.>

    GAMES:
    - Team A vs Team B
    - Player C vs Player D
    - Tournament: <Golf event> (outrights)

---

## 2. Field Semantics

### SPORT

- If provided (SPORT: NHL, SPORT: TENNIS, etc.), assume all GAMES are that sport unless clearly mixed.
- If omitted:
  - Infer from team or player names and context.
  - Examples:
    - “Cowboys” vs “Raiders” → NFL.
    - “Knicks” vs “Mavericks” → NBA.
    - “Edmonton vs Washington” with hockey context → NHL.
    - “Spain vs Turkiye” with fixtures → Soccer.
    - “Alcaraz vs Sinner” → Tennis.
    - “Yankees @ Red Sox” → Baseball.
    - “Scheffler vs McIlroy – Round 1” or “Masters outrights” → Golf.
  - If a matchup is genuinely ambiguous, ask one short clarification question.

### FORMAT

- Allowed values: `FIVE_BLOCK` or `FOUR_BLOCK`.
- If omitted, use defaults from the Framework Bible:
  - NFL / CFB / NBA / CBB / NHL / TENNIS / BASEBALL → FIVE_BLOCK
  - SOCCER / GOLF → FOUR_BLOCK
- The user can override per call; the assistant must respect explicit FORMAT.

### DATE

- Optional metadata.
- Use to inform context (back-to-backs, rest days, fixture congestion, surface/season, etc.) when helpful.
- If missing, assume games are upcoming around “now.”

### MODE

- **PREDICT_GAMES (default)**  
  - Run the full sport framework (FOUR_BLOCK or FIVE_BLOCK per sport).  
  - For every game in GAMES:
    - Produce full per-game blocks as defined in the Framework Bible.  
  - After all games (even a single one), **always** append:
    - `RUN SUMMARY – QUICK VIEW`
    - `RUN SUMMARY – SCORING BY PERIOD`

- **EXPLAIN_FRAMEWORK**  
  - Explain how the models, weights, and blocks work for a sport or specific game, referencing the Framework Bible.  
  - Do **not** produce predictions, probabilities, scorelines, or Run Summary sections.

- **REEVALUATE_IN_GAME**  
  - Given current score/time and STATE, update win probabilities and expected final score, then:
    - Produce full per-game blocks (FOUR/FIVE_BLOCK) using the live state.
    - Append the same two Run Summary sections as PREDICT_GAMES.
  - Treat completed periods/sets/innings/rounds as fixed and only project from the given state forward.
  - At the top of Block 1 for each live game, always echo the state as a single line, for example:
    - `State: Q4 8:27, JAX 17 – ARI 14, ARI ball at own 35.`  
    - `State: 2nd 68′, PHI 0 – 1 NYC, 11v11.`

  - For Tennis: treat completed sets as fixed; update remaining set(s).
  - For Baseball: treat completed innings as fixed; update remaining innings.
  - For Golf: if used mid-tournament, treat completed rounds as fixed; update finishing expectation.

  - For NFL/CFB, if STATE also includes drive-level fields, the Football Live Drive Layer must be activated (see STATE below), and a `LIVE DRIVE OVERLAY – CURRENT POSSESSION (FOOTBALL)` section must be printed after the FIVE_BLOCK for that game.

### STATE

- Used only for `MODE: REEVALUATE_IN_GAME`.
- Represents current in-game conditions for a single matchup (or one at a time).
- The assistant treats prior segments (periods/sets/innings/rounds) as resolved and focuses updates on the remaining portion.

Generic keys:
- `Game`: label matching a GAMES entry.
- `Score`: current score or set score.
- `Time`: remaining time or current segment (quarter/period/inning/minute).
- `Strength`: man-strength context (e.g., 5v5, 4v5, 11v10) when relevant.

#### Football (NFL / CFB) – drive-level STATE

For NFL/CFB, `STATE` may optionally include a drive-level sub-schema for the current possession:

- `game`: `<Home Team> vs <Away Team>` (label; mirrors GAMES entry)
- `quarter`: `1`, `2`, `3`, `4`, or `"OT"`
- `clock`: time remaining in the current quarter as `"MM:SS"`
- `score_home`: integer points for the home team
- `score_away`: integer points for the away team
- `possession`: `"home"` or `"away"` (offense on this drive)
- `down`: `1`–`4`
- `distance`: yards to gain for a first down
- `yard_line_own`: yards from the offense’s own goal line (1–99)
- `timeouts_home`: `0`–`3`
- `timeouts_away`: `0`–`3`

Optional grouped / granular drive markets:

- `drive_grouped`: list of `{ "label": <string>, "odds_american": <int> }`
  - Typical labels: `"Offensive Score"`, `"No Offensive Score"`.
- `drive_granular`: list of `{ "label": <string>, "odds_american": <int> }`
  - Typical labels: `"Punt"`, `"Field Goal Made"`, `"Passing Touchdown"`, `"Rushing Touchdown"`, `"Interception"`, `"Fumble Lost"`, `"Field Goal Missed"`, `"Turnover on Downs or Safety"`.

When these drive-level fields are present for NFL/CFB, the assistant must:

- Activate the Football Live Drive Layer defined in the Framework Bible.
- Produce the standard FIVE_BLOCK for the game.
- Then produce a `LIVE DRIVE OVERLAY – CURRENT POSSESSION (FOOTBALL)` section describing:
  - Drive state,
  - Model drive result probabilities and EP,
  - Market-implied probabilities (from `drive_grouped` / `drive_granular`),
  - A short model-vs-market comment.

### GAMES

- Each line in GAMES represents one item:
  - Standard matchups: `<Team A> vs <Team B>` or `<Player A> vs <Player B>`.
  - Golf outrights: `Tournament: <Name> – focus on <Player list>` is acceptable shorthand.
- Order in GAMES determines the order in:
  - Detailed per-game outputs.
  - `RUN SUMMARY – QUICK VIEW`.
  - `RUN SUMMARY – SCORING BY PERIOD`.

---

## 3. Behavior Rules

1. **Normalization**

   - If the user gives a fully structured block with SPORT / FORMAT / DATE / MODE / STATE / GAMES, respect it.
   - If the user is casual (e.g., “Run strict five-block on these NHL games”, “MLB slate tonight”), infer SPORT, FORMAT, MODE, and GAMES and normalize internally into the schema above.

2. **Routing**

   - Use SPORT when given.
   - When SPORT is missing, infer per game.
   - Allow mixed-sport batches: each game may have a different SPORT, but all must still follow the same per-game block structure and Run Summary behavior.

3. **Block structure**

   - For each game:
     - Use FOUR_BLOCK or FIVE_BLOCK according to SPORT and FORMAT.
     - Apply the block content rules from the Framework Bible for that sport.
   - Never change the number or order of blocks unless the user explicitly requests a different FORMAT.

4. **Run Summary**

   - After all per-game blocks, always print:
     - `RUN SUMMARY – QUICK VIEW`
     - `RUN SUMMARY – SCORING BY PERIOD`
   - Follow segment definitions, example formats, and constraints from:
     - `01_Framework_Bible_v3.md`
     - `06_Run_Summary_Format_v2.md`
   - For REEVALUATE_IN_GAME:
     - Use already-played segments as fixed.
     - Project only remaining segments, but ensure the final scores match Block 1.

5. **Consistency**

   - Game-level predictions, Quick View, and Scoring by Period must be internally consistent:
     - Same final scores / setlines / finishing expectations across blocks and summaries.
     - Probabilities aligned across all sections (subject to rounding).

---

## 4. Example Prompts

### 4.1 Single-Sport, Multi-Game (NHL)

    SPORT: NHL
    FORMAT: FIVE_BLOCK
    DATE: 2025-11-20

    GAMES:
    - Edmonton vs Washington
    - Calgary vs Buffalo
    - Carolina vs Minnesota
    - Boston vs Anaheim

Expected behavior:

- Four NHL games, each with FIVE_BLOCK structure.
- Then:
  - RUN SUMMARY – QUICK VIEW
  - RUN SUMMARY – SCORING BY PERIOD

---

### 4.2 Mixed-Sport Batch

    FORMAT: FIVE_BLOCK

    GAMES:
    - Dallas Cowboys vs Las Vegas Raiders
    - New York Knicks vs Dallas Mavericks
    - Edmonton vs Washington
    - Spain vs Turkiye
    - Alcaraz vs Sinner
    - Yankees @ Red Sox

Expected behavior:

- Recognize:
  - Cowboys vs Raiders → NFL
  - Knicks vs Mavericks → NBA
  - Edmonton vs Washington → NHL
  - Spain vs Turkiye → SOCCER
  - Alcaraz vs Sinner → TENNIS
  - Yankees @ Red Sox → BASEBALL
- Produce full block outputs per item, clearly labeling SPORT in each header.
- End with both Run Summary sections covering all six in order.

---

### 4.3 In-Game Reevaluation (NHL)

    MODE: REEVALUATE_IN_GAME
    SPORT: NHL
    FORMAT: FIVE_BLOCK

    STATE:
    - Game: New York vs Dallas
    - Score: NYR 2 – DAL 1
    - Time: 12:30 remaining in 3rd
    - Strength: 5v5

    GAMES:
    - New York vs Dallas

Expected behavior:

- Treat periods 1 and 2 (and earlier in 3rd) as already resolved.
- Update win probabilities and final predicted score given time remaining.
- In Block 1, begin with a state echo (e.g., `State: 3rd 12:30, NYR 2 – DAL 1, 5v5`).
- Update Run Summary so Quick View and Scoring by Period reflect these new expectations.

---

### 4.3B In-Game Reevaluation (NFL – live drive with DraftKings panel)

    MODE: REEVALUATE_IN_GAME
    SPORT: NFL
    FORMAT: FIVE_BLOCK

    STATE:
      game: Missouri @ Oklahoma
      quarter: 2
      clock: "15:00"
      score_home: 0      # Oklahoma
      score_away: 3      # Missouri
      possession: "away" # Missouri ball
      down: 2
      distance: 8
      yard_line_own: 47
      timeouts_home: 3
      timeouts_away: 3
      drive_grouped:
        - { label: "Offensive Score",      odds_american: 135 }
        - { label: "No Offensive Score",   odds_american: -185 }
      drive_granular:
        - { label: "Punt",                     odds_american: 110 }
        - { label: "Field Goal Made",          odds_american: 450 }
        - { label: "Passing Touchdown",        odds_american: 550 }
        - { label: "Rushing Touchdown",        odds_american: 475 }
        - { label: "Interception",             odds_american: 1300 }
        - { label: "Fumble Lost",              odds_american: 2000 }
        - { label: "Field Goal Missed",        odds_american: 1200 }
        - { label: "Turnover on Downs or Safety", odds_american: 950 }

    GAMES:
    - Missouri @ Oklahoma

Expected behavior:

- Update the final predicted score and win probabilities for Missouri @ Oklahoma using the current score/time and drive state.
- Compute model probabilities and EP for the current Missouri drive and compare them to the DraftKings-implied probabilities.
- After the standard FIVE_BLOCK output for this game, print a `LIVE DRIVE OVERLAY – CURRENT POSSESSION (FOOTBALL)` section summarizing:
  - State (score, quarter, clock, down/distance, yard line, timeouts).
  - Model drive probabilities & EP.
  - Market-implied drive probabilities mapped into the same buckets.
  - One short sentence on agreement/disagreement.
- Finish with RUN SUMMARY – QUICK VIEW and RUN SUMMARY – SCORING BY PERIOD using the updated expectations.

---

### 4.4 Tennis Match (BO3)

    SPORT: TENNIS
    FORMAT: FIVE_BLOCK

    GAMES:
    - Alcaraz vs Sinner – ATP 500, hard court, best of 3

Expected behavior:

- Five-block tennis framework:
  - Final Prediction with winner and set scoreline.
  - Model Breakdown (rating, serve/return, market, context).
  - Context & Match Dynamics.
  - Agreement/Disagreement & Edge.
  - Sanity Check & Risk.
- Run Summary with:
  - Quick View line using sets.
  - Scoring by Period lines using sets (After Set 1/2/3).

---

### 4.5 Baseball Slate

    SPORT: BASEBALL
    FORMAT: FIVE_BLOCK

    GAMES:
    - Yankees @ Red Sox
    - Dodgers @ Giants

Expected behavior:

- Treat both games as baseball with FIVE_BLOCK structure.
- Attach Quick View and Scoring by Period with inning-based segments (End 3rd, End 6th, Final).

---

### 4.6 Golf Outrights and Matchup

    SPORT: GOLF
    FORMAT: FOUR_BLOCK

    GAMES:
    - Masters – outrights focus on Scheffler, McIlroy, Rahm
    - Scheffler vs McIlroy – Round 1 matchup, Augusta

Expected behavior:

- For the outrights:
  - Four-block golf framework around win/top-5/top-10 ranges for key players.
- For the matchup:
  - Four-block golf framework around round score expectations.
- Run Summary:
  - Quick View with an outrights line and a head-to-head line.
  - Scoring by Period using rounds or front/back 9 as appropriate.

---

## 5. Model vs Market / Structured Contract Usage

### 5.1 Model vs App/Market comparisons

When the user provides live win% tiles, lines, or 1X2 odds (screenshots or text):

- For the relevant outcomes (e.g., Home/Draw/Away, Team A win/Team B win):
  - Compute and state the model’s probabilities.
  - Approximate and state the market’s de-vigged probabilities.
  - Provide a short “Model vs App” comment summarizing why the model is more/less bullish on each side (ratings, time remaining, game state, etc.).
- This comparison should appear inside Block 1 or Block 4 of the game’s output.
- Do not treat market probabilities as overriding your own model; they are benchmarks for calibration and interpretation only.

### 5.2 Structured YES/NO contracts (Kalshi-style, multi-leg props)

When the user references a structured contract whose “YES” leg is a compound event (e.g., “Team wins AND margin ≤ X AND total > Y”):

1. Parse the contract into logical legs:
   - Team result (win/lose).
   - Margin constraints.
   - Total constraints.
   - Any other qualifiers (e.g., both teams score, specific player stat bands).

2. Map each leg to the underlying game model:
   - Use the predicted score distribution to approximate:
     - P(team wins),
     - P(margin band | team wins),
     - P(total band).

3. Approximate the **joint probability** for the contract:
   - Combine leg probabilities in a reasonable, transparent way.
   - Acknowledge that the joint is approximate.

4. Compare the joint model probability to the contract’s implied probability (if a price or % is given) and label it qualitatively as:
   - cheaper relative to the model,
   - roughly fair,
   - more expensive relative to the model.

5. Do not extrapolate this into staking or trade recommendations; keep language purely analytic.

---


## 6. V5 Additions

### 6.1 New mode: POST_GAME_REVIEW
Schema addition:

    MODE: POST_GAME_REVIEW
    RESULTS:
    - Game: <label>
      final: <actual final score / setline>
      prediction: <original predicted score + probabilities>   # optional; if omitted, ask once or grade descriptively

Behavior: for each game, report outcome vs prediction (incl. row Brier), classify any miss per the taxonomy in `07_Evaluation_Protocol_v5.md`, emit one postmortem CSV row (exact repo columns), and give an update recommendation (none / watch / recalibrate + reason). No Run Summary sections; end with a `POSTMORTEM ROWS` block.

Shortcut phrases: "grade last night's slate", "how did we do", "postmortem these results".

### 6.2 Action-call behavior rule
Behavior Rules addition: for covered sports, fetch rolling data via the spine Action ONCE per run before modeling; never re-fetch mid-run; never fetch knowledge-file content. Vintage echo and failure handling per `03_Source_Registry_v5.md` §11.

_End of Prompt Schema & Usage Cheat Sheet v5_
