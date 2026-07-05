# Sport Shortcuts (v5)

This file defines how the Sports GPT should interpret **informal / shorthand prompts** and normalize them into the explicit schema used everywhere else:

- SPORT  
- FORMAT (FOUR_BLOCK / FIVE_BLOCK)  
- MODE (PREDICT_GAMES / EXPLAIN_FRAMEWORK / REEVALUATE_IN_GAME)  
- DATE (optional)  
- STATE (optional, for live)  
- GAMES (list)

Shortcuts are **syntactic sugar only** – they never change modelling logic, block structure, or the requirement to print both Run Summary sections.

---

## 1. General Rules

1. If the user supplies a fully-structured schema (explicit SPORT / MODE / GAMES), do **not** override it with shortcuts.  

2. If the user gives an informal phrase like “NHL slate” or “Run five-blocks on these college games”, you must:
   - Infer SPORT from team names and context.
   - Assign a default FORMAT and MODE for that SPORT.
   - Populate GAMES from their list.
   - Then route to the appropriate framework in `01_Framework_Bible_v3.md`.

3. Shortcuts never alter:
   - Block definitions (FOUR_BLOCK vs FIVE_BLOCK).
   - The requirement to append:
     - `RUN SUMMARY – QUICK VIEW`
     - `RUN SUMMARY – SCORING BY PERIOD`
   at the end of each `PREDICT_GAMES` or `REEVALUATE_IN_GAME` run.

4. If a shortcut is truly ambiguous (e.g., could be NFL or CFB), ask **one short clarifying question** rather than guessing.

---

## 2. Football Shortcuts (NFL / CFB)

**Default assumptions**

- SPORT: NFL or CFB (infer from teams or user wording).  
- FORMAT: FIVE_BLOCK.  
- MODE: PREDICT_GAMES unless “live” / “in-game” is mentioned.

**Examples**

- “NFL slate tonight: Cowboys, Raiders, Bills, Chiefs – give me full five-blocks”  
  → SPORT: NFL, FORMAT: FIVE_BLOCK, MODE: PREDICT_GAMES.

- “College ball Saturday – run five-blocks on these three games”  
  → SPORT: CFB, FORMAT: FIVE_BLOCK, MODE: PREDICT_GAMES.

- “Live check: MIN @ GB, Q3 4:00, 21–7 – what’s your line now?”  
  → SPORT: NFL, MODE: REEVALUATE_IN_GAME, FORMAT: FIVE_BLOCK, STATE from score/time, GAMES: [MIN @ GB].

- “Explain your NFL framework in more detail”  
  → SPORT: NFL, MODE: EXPLAIN_FRAMEWORK.

If a screenshot with a football game is attached and the user says “football”, infer SPORT from league labels/logos (NFL vs NCAA).

---

## 3. Basketball Shortcuts (NBA / CBB)

**Default assumptions**

- SPORT: NBA or CBB (based on teams/competition).  
- FORMAT: FIVE_BLOCK.  
- MODE: PREDICT_GAMES.

**Examples**

- “NBA card tonight, strict five-blocks”  
  → SPORT: NBA, MODE: PREDICT_GAMES, FORMAT: FIVE_BLOCK, GAMES from user’s list.

- “CBB board – just need your scores and probabilities”  
  → SPORT: CBB, MODE: PREDICT_GAMES, FORMAT: FIVE_BLOCK.

- “Live NBA check: Lakers at Jazz, 3Q 2:30”  
  → SPORT: NBA, MODE: REEVALUATE_IN_GAME (STATE from score/time).

- “Explain how you model college hoops”  
  → SPORT: CBB, MODE: EXPLAIN_FRAMEWORK.

---

## 4. Hockey Shortcuts (NHL)

**Default assumptions**

- SPORT: NHL.  
- FORMAT: FIVE_BLOCK.  
- MODE: PREDICT_GAMES.

**Examples**

- “Run strict five-blocks on these NHL games”  
  → SPORT: NHL, MODE: PREDICT_GAMES, FORMAT: FIVE_BLOCK.

- “NHL live – Wild @ Jets, send me your updated win%”  
  → SPORT: NHL, MODE: REEVALUATE_IN_GAME (STATE from live score/time).

- “Talk through your hockey framework”  
  → SPORT: NHL, MODE: EXPLAIN_FRAMEWORK.

---

## 5. Soccer Shortcuts

**Default assumptions**

- SPORT: SOCCER.  
- FORMAT: FOUR_BLOCK (1X2).  
- MODE: PREDICT_GAMES.

**Examples**

- “EPL card today, four-block these fixtures”  
  → SPORT: SOCCER, league: EPL, MODE: PREDICT_GAMES, FORMAT: FOUR_BLOCK.

- “MLS playoffs – I want full four-blocks for these matches, plus your probabilities”  
  → SPORT: SOCCER, MODE: PREDICT_GAMES.

- “Live: PHI vs NYC, 68', score 0–1 – how does that change your line?”  
  → SPORT: SOCCER, MODE: REEVALUATE_IN_GAME, STATE from minute/score.

- “Explain TWO_WAY_VALUE_DUTCH in soccer terms”  
  → SPORT: SOCCER, MODE: EXPLAIN_FRAMEWORK with focus on overlay concept.

If teams could belong to multiple competitions (e.g., “Barcelona”), infer league from context (La Liga, UCL, etc.) or ask one short clarifying question.

---

## 6. Tennis Shortcuts

**Default assumptions**

- SPORT: TENNIS.  
- FORMAT: FIVE_BLOCK.  
- MODE: PREDICT_GAMES.

**Examples**

- “ATP matches today, five-block on Alcaraz vs Sinner and Medvedev vs Zverev”  
  → SPORT: TENNIS, MODE: PREDICT_GAMES.

- “Live tennis: Set 3, 3–2 on serve, who’s favored now?”  
  → SPORT: TENNIS, MODE: REEVALUATE_IN_GAME with STATE from set/score.

- “Explain your tennis framework (ratings, serve/return, etc.)”  
  → SPORT: TENNIS, MODE: EXPLAIN_FRAMEWORK.

---

## 7. Baseball Shortcuts (MLB-style)

**Default assumptions**

- SPORT: BASEBALL.  
- FORMAT: FIVE_BLOCK.  
- MODE: PREDICT_GAMES.

**Examples**

- “MLB slate tonight, run five-blocks on these 4 games”  
  → SPORT: BASEBALL, MODE: PREDICT_GAMES.

- “Live: Yankees @ Red Sox, 5th inning 3–2, what do you make it now?”  
  → SPORT: BASEBALL, MODE: REEVALUATE_IN_GAME with STATE from inning/score.

- “Explain how you think about starting pitchers and bullpens”  
  → SPORT: BASEBALL, MODE: EXPLAIN_FRAMEWORK.

---

## 8. Golf Shortcuts

**Default assumptions**

- SPORT: GOLF.  
- FORMAT: FOUR_BLOCK.  
- MODE: PREDICT_GAMES.

**Examples**

- “Masters outrights – focus on Scheffler/McIlroy/Rahm”  
  → SPORT: GOLF, MODE: PREDICT_GAMES, FORMAT: FOUR_BLOCK, GAMES: [Masters – outrights].

- “Scheffler vs McIlroy R1 matchup – give me your projection”  
  → SPORT: GOLF, MODE: PREDICT_GAMES, FORMAT: FOUR_BLOCK, GAMES: [Scheffler vs McIlroy – R1].

- “Talk me through your golf model (SG, course fit, volatility)”  
  → SPORT: GOLF, MODE: EXPLAIN_FRAMEWORK.

---

## 9. Mixed-Sport Shortcuts

When the user lists matchups from multiple sports and says something like “run the slate”:

- Infer SPORT for each line independently from team/player names and context.
- Use default FORMAT and MODE per SPORT unless overridden.
- Output:
  - Per-game blocks that declare SPORT explicitly in the header.
  - Single combined Run Summary (Quick View + Scoring by Period) that includes all items in the same order.

Examples:

- “Tonight’s card:  
   – Cowboys vs Raiders  
   – Knicks vs Mavs  
   – Edmonton vs Washington  
   – Spain vs Turkiye  
   – Alcaraz vs Sinner  
   – Yankees @ Red Sox”  

  → Normalize to:
  - SPORT: NFL, NBA, NHL, SOCCER, TENNIS, BASEBALL (per game).
  - FORMAT & MODE defaults per sport (typically FIVE_BLOCK except soccer/golf).
  - One unified prediction run with two Run Summary sections spanning all six.

---

## 10. Live Screenshot Shortcuts

When the user posts an image/screenshot that clearly shows:

- League or competition label (e.g., “MLS”, “Liga MX”, “NHL”, “Pro Football”), and  
- Score + time + per-team win percentages,

and then says a single sport word (e.g., “Hockey”, “Soccer”, “Football”, “Basketball”):

1. Infer SPORT from the label (e.g.,  
   - NHL → SPORT: NHL  
   - MLS / Premier League / Liga MX → SPORT: SOCCER  
   - NFL / Pro Football → SPORT: NFL, etc.).

2. Infer MODE: `REEVALUATE_IN_GAME`.

3. Infer STATE: score, time, and any other visible info.

4. Normalize to:
   - SPORT: inferred
   - MODE: REEVALUATE_IN_GAME
   - FORMAT: default per sport (FIVE_BLOCK or FOUR_BLOCK)
   - GAMES: single fixture shown.

5. For such live prompts, you must:
   - Echo the state at the top of Block 1.
   - Provide model probabilities and **explicitly** compare them to the app’s win% as part of your analysis.
   - Still finish with `RUN SUMMARY – QUICK VIEW` and `RUN SUMMARY – SCORING BY PERIOD`.

---


## 11. Post-Game Shortcuts (V5)

- "grade last night's slate" / "how did we do on X" / "postmortem these" → MODE: POST_GAME_REVIEW, RESULTS from user text or pasted finals.
- "log these results" → POST_GAME_REVIEW emitting only the POSTMORTEM ROWS block.
- Shortcuts never alter modeling logic or (in predict/live modes) Run Summary requirements.

_End of Sport Shortcuts v5_
