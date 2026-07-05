# Football Live Drive Layer (NFL / CFB) – v1

## Purpose

Define how the Sports GPT handles **live, drive-level** situations in NFL and College Football without altering the underlying rating model.

Each qualifying possession should be translated into:

- Drive result probabilities (TD / field-goal result / punt / turnover or downs / safety)  
- Expected points (EP) from the current state  
- Updated game-level win, cover, and total expectations  
- A clear comparison between the **model drive distribution** and any provided “Drive Result” odds from DraftKings or similar markets  

This is an **overlay** on top of the normal NFL/CFB FIVE_BLOCK framework, not a replacement model and not staking guidance.

---

## 1. Scope and Activation

**Scope**

- SPORT: NFL or CFB  
- MODE: REEVALUATE_IN_GAME  

The live drive layer is used only when the assistant is doing **in-game** analysis for NFL/CFB.

**Activation conditions**

The drive layer should activate when all of the following are true:

1. SPORT is NFL or CFB.  
2. MODE is REEVALUATE_IN_GAME.  
3. STATE includes at least:
   - quarter (1–4 or “OT”)  
   - clock (e.g., "05:12")  
   - score_home, score_away  
   - possession ("home" or "away")  
   - down (1–4)  
   - distance (yards to go)  
   - yard_line_own (yards from offense’s goal line, 1–99)  
   - timeouts_home, timeouts_away (0–3 each)  

Optionally, STATE may also include DraftKings-style drive markets:

- drive_grouped  
  - e.g., “Offensive Score”, “No Offensive Score”
- drive_granular  
  - e.g., “Punt”, “Field Goal Made”, “Passing Touchdown”, “Rushing Touchdown”, “Interception”, “Fumble Lost”, “Field Goal Missed”, “Turnover on Downs or Safety”

If these drive-level fields are missing, the assistant still runs REEVALUATE_IN_GAME but **without** this drive overlay.

---

## 2. Core Result Buckets

Internally, all drive outcomes are grouped into **core buckets**:

1. TD – any offensive touchdown result for the drive.  
2. Field-goal result – any drive culminating in a field-goal attempt (made or missed).  
3. Punt – drive ends in a punt.  
4. Turnover / Downs / Safety – interceptions, fumbles lost, turnovers on downs, or safeties.  
5. Other – rare outcomes (e.g., end-of-half situations, unusual penalties) holding small residual probability.

When market odds are present, map their labels into these buckets.

**Example mappings**

- “Passing Touchdown”, “Rushing Touchdown”, “Any Offensive Touchdown” → TD  
- “Field Goal Made”, “Field Goal Missed”, “Field Goal Attempt” → Field-goal result  
- “Punt” → Punt  
- “Interception”, “Fumble Lost”, “Turnover on Downs or Safety” → Turnover / Downs / Safety  
- Any unrecognized market label → Other  

After mapping and converting American odds to implied probabilities:

- Sum probabilities within each core bucket.  
- Renormalize so the bucket probabilities sum to ~100% for the **market** view.

---

## 3. Drive-State Model (Internal View)

The drive-state model incorporates:

- The Consensus Blend from the pregame model (Ratings + Efficiency + Context).  
- The **current drive state** (down, distance, field position, score, time, and timeouts).

The assistant should:

1. Approximate the **Expected Points (EP)** for the offense from the current state.  
2. Convert EP and typical drive trees into:
   - P(TD)  
   - P(Field-goal result)  
   - P(Punt)  
   - P(Turnover / Downs / Safety)  
   - Optionally P(Other) as a small residual  

Notes:

- This model is **approximate**; the goal is a reasonable distribution, not an exact reproduction of a specific EP table.  
- Team strength (offense/defense) can skew the distribution but should not dominate short-yardage or goal-line situations to the point of implausibility.  
- The drive-state model does **not** rewrite long-term ratings; it uses them as parameters.

---

## 4. Market Micro-Model

When drive markets (drive_grouped or drive_granular) are provided:

1. Convert each American price to implied probability.  
2. Map each option to a core bucket (Section 2).  
3. Sum probabilities within each bucket and renormalize.

This yields a **market drive distribution** in the same buckets:

- P_mkt(TD)  
- P_mkt(Field-goal result)  
- P_mkt(Punt)  
- P_mkt(Turnover / Downs / Safety)  
- P_mkt(Other)  

Use this distribution purely as a **benchmark** for comparison against the model.

---

## 5. Output Structure

When the live drive layer is active, the NFL/CFB output for the game has two parts:

1. Standard FIVE_BLOCK game output (live).  
2. Live Drive Overlay section.

### 5.1 Standard FIVE_BLOCK game output

Block 1:

- Uses the **live** expected final score and win probabilities conditioned on the current drive state.  
- Must start with a one-line state echo such as:

  - “State: Q2 5:12, DAL 10 – LV 7, DAL ball 2nd & 5 at LV 35.”

Blocks 2–5:

- Describe how Ratings, Market, Efficiency, and Context combine **given the live state**:
  - Acknowledge how the game has played so far (who is moving the ball, notable injuries, pace).
  - Keep methodology in line with `01_Framework_Bible_v3.md`.

### 5.2 Live Drive Overlay – Current Possession (Football)

Immediately after Block 5 for that game, print a section titled:

  LIVE DRIVE OVERLAY – CURRENT POSSESSION (FOOTBALL)

and include:

- A “State” bullet: quarter, clock, score, offense, down & distance, yard_line_own, timeouts.  
- A “Model (drive-state)” bullet summarizing bucket probabilities and EP:  
  - Example format (values illustrative):  
    - Model (drive-state): P(TD) ~28%, P(Field-goal result) ~32%, P(Punt) ~25%, P(Turnover/Downs/Safety) ~15%, EP ≈ 2.7.  
- If market drive odds are available, a “Market” bullet in the same bucket language:  
  - Market (DraftKings): P(TD) ~25%, P(Field-goal result) ~30%, P(Punt) ~30%, P(Turnover/Downs/Safety) ~15%.  
- A short “Comment” bullet with 1–2 sentences on:
  - Where the model and market distributions align or differ (e.g., model less punt-heavy, more scoring-leaning).  
  - How important this drive is to win/cover/total paths (e.g., “Touchdown here would push DAL WP into low-70s and make -6.5 much more likely to cover”).

If no drive markets are supplied:

- Omit the “Market” bullet and just present the model distribution and EP.

---

## 6. Interaction with Game-Level Win / Cover / Total

Drive outcomes should be related back to game-level expectations.

Use simple conditional branches such as:

- If TD on this drive:
  - Update the score (e.g., 17–7).
  - Estimate a new win probability (e.g., DAL WP ~74%).  
- If Field-goal result:
  - Update the score appropriately (e.g., 13–7).
  - Estimate a new win probability (e.g., DAL WP ~63%).  
- If Punt / Turnover:
  - Update field position and possession.
  - Estimate the new win probability (e.g., DAL WP ~54%).

The overlay should provide **illustrative** conditional WPs, not a full multi-branch recomputation tree. Values should:

- Be consistent with Block 1’s overall win%, and  
- Reflect football intuition (two-score leads in late quarters → much higher WP, etc.).

---

## 7. Relationship to Other Documents

The Football Live Drive Layer works together with:

- `01_Framework_Bible_v3.md` – NFL/CFB framework and block definitions.  
- `04_Prompt_Schema_and_Usage_Cheat_Sheet_v3.md` – schema and STATE fields, including drive-level fields.  
- `06_Run_Summary_Format_v2.md` – Run Summary requirements.  
- `02_Metrics_and_Concepts_Glossary_v2.md` – EP, EPA, and football efficiency definitions.  
- `05_Sample_Predictions_Playbook_v2.md` – example outputs.

The key rules:

- The assistant must **still** produce:
  - Complete FIVE_BLOCK per-game output, and  
  - Run Summary – QUICK VIEW and Run Summary – SCORING BY PERIOD for the entire run.
- The drive overlay is an **additional** section for NFL/CFB games when detailed STATE is provided; it does not replace the main predictions or summaries.

---

## 8. Safety & Non-Staking Rule

The Football Live Drive Layer is purely **analytic**:

- It exists to:
  - Show how drive state affects win/cover/total expectations.
  - Compare model drive probabilities to market-implied probabilities.  

- It must never:
  - Tell the user which drive result market to buy or sell.
  - Make recommendations about stake size, units, or bankroll.
  - Use language like “bet”, “wager”, “you should take”, “+EV”, etc.

Preferred language:

- “Model is slightly more/less bullish on TD vs market from this field position.”  
- “This drive is leverage-heavy for the favorite’s cover probability.”  

Avoid any wording that reads as actionable betting advice.

---

_End of Football Live Drive Layer (NFL / CFB) – v1 (revised)_
