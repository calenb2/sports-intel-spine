# Run Summary Format (v5)

This file defines exactly how the Sports GPT must print the final two sections of every prediction run:

1. RUN SUMMARY – QUICK VIEW  
2. RUN SUMMARY – SCORING BY PERIOD  

These sections always appear after all per-game block outputs, **in this order**, for every `MODE: PREDICT_GAMES` and `MODE: REEVALUATE_IN_GAME` run (even for a single game, and even when in-progress).

`RUN SUMMARY – ADVANCED OVERLAY` is an optional third section used only when an advanced concept (e.g., TWO_WAY_VALUE_DUTCH) triggers.

---

## 1. General Rules

1. Cover all items in the current response, in the same order as the user listed them.  

2. Use headings exactly:
   - RUN SUMMARY – QUICK VIEW
   - RUN SUMMARY – SCORING BY PERIOD
   - (Optional) RUN SUMMARY – ADVANCED OVERLAY

3. Use short, scannable lines:
   - Numbered lists.
   - No long paragraphs.

4. Unless explicitly asked to evaluate past results, treat all summaries as **predictions** (or re-predictions from a live state), not post-mortems.

5. Ensure that:
   - Final scores/sets/finishing expectations in the summaries **match Block 1** of each game (within rounding).
   - Probabilities are consistent with the game blocks for that run.

---

## 2. RUN SUMMARY – QUICK VIEW

### Format

- Numbered list.
- One concise line per item; two lines max when needed (e.g., soccer three-way probabilities or complex golf outrights).

Generic templates:

**Two-outcome team or player sports**  
(NFL / CFB / NBA / CBB / NHL / TENNIS / BASEBALL / GOLF head-to-head)

Format:

  <index>. <Label> (<SPORT>) → <PREDICTED_SCORE_OR_SETLINE>, <winner> win ~<prob>%

Examples:

  1. Dallas Cowboys vs Las Vegas Raiders (NFL) → DAL 27 – LV 20, DAL win ~62%  
  2. Edmonton vs Washington (NHL) → EDM 4 – WSH 2, EDM win ~63%  
  3. Alcaraz vs Sinner (TENNIS) → ALC 2 sets – SIN 1 set, ALC win ~60%  
  4. Yankees @ Red Sox (BASEBALL) → NYY 5 – BOS 4, NYY win ~55%  
  5. Scheffler vs McIlroy – R1 (GOLF) → Scheffler 69 – McIlroy 70, Scheffler lower score ~58%

**Soccer (three-outcome)**

Format:

  <index>. <Team A> vs <Team B> (SOCCER) → <TEAM_A_SCORE> – <TEAM_B_SCORE>, P(<Team A>) ~XX%, Draw ~YY%, P(<Team B>) ~ZZ%

Example:

  6. Spain vs Turkiye (SOCCER) → ESP 2 – TUR 1, P(ESP) ~54%, Draw ~26%, P(TUR) ~20%

**Golf outrights**

Format:

  <index>. <Tournament Name> (GOLF) → <key player summary of win/top-X probabilities>

Example:

  7. Masters Outrights (GOLF) → Scheffler primary favorite (win ~14%, top-5 ~45%, top-10 ~70%; McIlroy/Rahm next tier)

Constraints:

- Final scores/setlines must match Block 1 for each item (within rounding).  
- Probabilities must be consistent and sum to ~100% for two- and three-way outcomes.  
- For `MODE: REEVALUATE_IN_GAME`, the Quick View still reflects **updated predictions** (from the current state) rather than past results.

---

## 3. RUN SUMMARY – SCORING BY PERIOD

### Overall Layout

- Numbered list by item.
- For each item:
  - First line: game/match/tournament label.
  - Following lines: cumulative predicted scores at the end of each segment.
  - Mark the highest scoring or most decisive segment clearly.

For live (`REEVALUATE_IN_GAME`) runs:

- Treat already-played segments as **fixed**.
- Only segment predictions for the remaining time may change.
- The final cumulative scores must still match the updated Block 1 predictions.

### Segment Definitions

- NFL / CFB  
  - End Q1  
  - Halftime (End Q2)  
  - End Q3  
  - Final (End Q4)

- NBA  
  - End Q1  
  - Halftime (End Q2)  
  - End Q3  
  - Final (End Q4)

- CBB  
  - Halftime  
  - Final

- NHL  
  - End P1  
  - End P2  
  - Final (End P3)

- Soccer  
  - Halftime  
  - Final  
  - Only add ET1 / ET2 if the user explicitly asks to include extra time.

- Tennis  
  - After Set 1  
  - After Set 2  
  - After Set 3 (and Set 4/5 if projected)  
  - Use sets won, not games, unless the user specifically asks for game counts.

- Baseball  
  - End 3rd inning  
  - End 6th inning  
  - Final (End 9th)  
  - If the prediction implies extras, still list “Final” with the expected final score.

- Golf  
  - For 18-hole head-to-head matchups:
    - End Front 9  
    - Final (18 holes)
  - For 72-hole tournaments (when profiling a single player/leader or short list):
    - End R1  
    - End R2  
    - End R3  
    - Final (End R4)  
    - Use strokes relative to par or relative to field as appropriate.

### Example Formats

NFL Example:

  RUN SUMMARY – SCORING BY PERIOD

  1. Dallas Cowboys vs Las Vegas Raiders  
     - End Q1: DAL 7 – LV 3  
     - Halftime: DAL 13 – LV 10  
     - End Q3: DAL 20 – LV 13  
     - Final: DAL 27 – LV 20  ← highest scoring quarter expected is Q4  

NHL Example:

  2. Edmonton vs Washington  
     - End P1: EDM 1 – WSH 0  
     - End P2: EDM 3 – WSH 2  ← highest scoring period expected  
     - End P3: EDM 4 – WSH 2 (Final)  

Soccer Example:

  3. Spain vs Turkiye  
     - Halftime: ESP 1 – TUR 0  
     - Final: ESP 2 – TUR 1  ← second half expected to be more open and higher scoring  

Tennis Example:

  4. Alcaraz vs Sinner  
     - After Set 1: ALC 1 – SIN 0  
     - After Set 2: ALC 1 – SIN 1  
     - After Set 3: ALC 2 – SIN 1 (Final)  ← deciding set expected to be tight but decisive  

Baseball Example:

  5. Yankees @ Red Sox  
     - End 3rd: NYY 1 – BOS 1  
     - End 6th: NYY 3 – BOS 3  
     - Final (End 9th): NYY 5 – BOS 4  ← middle-to-late innings expected to see most scoring clusters  

Golf Matchup Example:

  6. Scheffler vs McIlroy – R1  
     - End Front 9: Scheffler −2, McIlroy −1  
     - Final (18): Scheffler −3, McIlroy −2  ← back nine slightly more volatile with key scoring holes  

### Constraints

1. Cumulative Scores  
   - Scores must be non-decreasing for each side across segments.  
   - Final cumulative scores must match the final scores or setlines from Quick View / Block 1.

2. Realism  
   - Respect typical scoring distributions from `02_Metrics_and_Concepts_Glossary_v2.md`.  
   - High-scoring segments should be plausible relative to the overall total.  
   - In live runs, already-known segment scores must not be altered.

3. Highlighting Highest Scoring / Decisive Segment  
   - Mark exactly one segment (or clearly note “tied”) as highest scoring or most decisive using a short arrow and phrase, for example:
     - ← highest scoring period expected  
     - ← second half expected to be most open and high scoring  
     - ← deciding set expected to be most volatile  

---

## 4. RUN SUMMARY – ADVANCED OVERLAY (Optional)

### Purpose

Provide an optional third summary section when at least one game triggers an advanced overlay concept (currently `TWO_WAY_VALUE_DUTCH`). This section is **analytical only** and must not contain staking, units, or “how to bet” language.

### Header

If used, print after the other two sections:

  RUN SUMMARY – ADVANCED OVERLAY

### Format

- One line per qualifying item, in the same order used earlier in the Run Summary.
- Generic template:

  <index>. <Label> (<SPORT>) → Overlay: <concept or "none">; <short reason>

Examples:

  • 3A. Brighton vs Brentford (SOCCER) → Overlay: TWO_WAY_VALUE_DUTCH; both win sides show positive edge vs market, draw slightly overpriced.  
  • 5. Spain vs Turkiye (SOCCER) → Overlay: none; draw not clearly overpriced and one win side lacks a model edge.

### Rules

1. Only include items where an advanced concept actually triggers; otherwise omit the entire section.  
2. Keep each line to one sentence (two max). Focus on:
   - Whether the concept applies; and
   - A brief “why” tied to model vs market probabilities.
3. Do **not** mention stake sizes, units, bankroll, or explicit betting instructions.  
4. If no games qualify, omit `RUN SUMMARY – ADVANCED OVERLAY` entirely.

---


## 5. V5 Addendum — Confidence suffix

Every RUN SUMMARY – QUICK VIEW line ends with the game's confidence grade in parentheses:

    1. Spain vs Turkiye (SOCCER) → ESP 2 – TUR 1, P(ESP) ~54%, Draw ~26%, P(TUR) ~20% (Conf B+)

The grade must match Block 1 exactly. Scoring-by-Period and Advanced Overlay formats are unchanged.

_End of Run Summary Format v5_
