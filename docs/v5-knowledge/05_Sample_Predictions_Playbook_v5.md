# Sample Predictions Playbook (v5)

These are stylized examples of “good” outputs for the Sports GPT. They demonstrate:

- Proper block structure (FOUR_BLOCK / FIVE_BLOCK per sport).
- REQUIRED Run Summary sections at the end of every run.
- Live / in-game handling (including the Football Live Drive Overlay).
- Model vs Market/App comparisons where relevant.
- Usage of advanced overlays like TWO_WAY_VALUE_DUTCH (analysis only, never staking advice).

Scores and probabilities are illustrative, not factual.

---

## 1. NHL Example

### Game Output

GAME: Edmonton vs Washington — SPORT: NHL — FORMAT: FIVE_BLOCK

**Block 1 – Final Prediction**

- Predicted final: Edmonton 4 – Washington 2.  
- Win probabilities: EDM ~63%, WSH ~37%.  
- Edmonton’s stronger 5v5 xG profile and deeper forward depth tilt the matchup toward the Oilers.

**Block 2 – Model Breakdown**

- Rating Model: Slight edge to Edmonton based on season-long performance.  
- xG / Shot Quality Model: Edmonton generates more high-danger chances at even strength.  
- Special Teams Model: Edmonton’s power play is more dangerous; penalty kills roughly even.  
- Context Model: Both teams on equal rest; travel burden modest.

**Block 3 – Context & Schedule**

- No major injuries to Edmonton’s top line reported.  
- Washington mid-road trip but not on a back-to-back.  
- Edmonton at home with last change.

**Block 4 – Agreement/Disagreement & Edge**

- Rating, xG, and Special Teams all lean Edmonton.  
- Context is mostly neutral.  
- Overall: clear but not overwhelming advantage to Edmonton.

**Block 5 – Sanity Check & Risk**

- Hot Washington goaltending or Edmonton penalty trouble could flip the script.  
- Low-event game increases variance and helps the underdog.  
- If late injuries or goalie changes emerge, revise the prediction.

---

### Run Summary Sections (NHL)

**RUN SUMMARY – QUICK VIEW**

1. Edmonton vs Washington (NHL) → EDM 4 – WSH 2, EDM win ~63%

**RUN SUMMARY – SCORING BY PERIOD**

1. Edmonton vs Washington  
   - End P1: EDM 1 – WSH 0  
   - End P2: EDM 3 – WSH 2  ← highest scoring period expected  
   - Final (End P3): EDM 4 – WSH 2  

---

## 2. NFL Example (Pre-Game)

### Game Output

GAME: Dallas Cowboys vs Las Vegas Raiders — SPORT: NFL — FORMAT: FIVE_BLOCK

**Block 1 – Final Prediction**

- Predicted final: Cowboys 27 – Raiders 20.  
- Win probabilities: DAL ~62%, LV ~38%.  
- Dallas combines a more efficient offense with a stronger defense, especially against the pass.

**Block 2 – Model Breakdown**

- Rating Model: Cowboys graded a tier above the Raiders.  
- Market/Odds Model: Market implies a modest favorite, aligning with Dallas by a field goal-plus.  
- Efficiency Model: Dallas ahead in EPA/play on both sides of the ball over recent weeks.  
- Context Model: Dallas at home, both teams on standard rest.

**Block 3 – Context & Schedule**

- No major QB injuries; a few minor skill-position issues on both sides.  
- Dallas home-field advantage and familiarity with turf.  
- Raiders traveling but not in a brutal schedule spot.

**Block 4 – Agreement/Disagreement & Edge**

- All four models lean Dallas; strongest agreement from Ratings and Efficiency.  
- Raiders’ path is mostly via turnovers and explosive passes.

**Block 5 – Sanity Check & Risk**

- Turnover luck or explosive plays could create an upset.  
- If Dallas struggles in the red zone or commits key penalties, score gap could shrink or flip.  
- Weather could dampen scoring if conditions deteriorate.

---

### Run Summary Sections (NFL – Pre-Game)

**RUN SUMMARY – QUICK VIEW**

2. Dallas Cowboys vs Las Vegas Raiders (NFL) → DAL 27 – LV 20, DAL win ~62%

**RUN SUMMARY – SCORING BY PERIOD**

2. Dallas Cowboys vs Las Vegas Raiders  
   - End Q1: DAL 7 – LV 3  
   - Halftime: DAL 14 – LV 10  
   - End Q3: DAL 20 – LV 13  
   - Final: DAL 27 – LV 20  ← Q4 expected to be the most decisive quarter  

---

## 2A. NFL In-Game Live Drive Example (with Drive Layer & Model vs App)

### Game Output (Live)

GAME: Dallas Cowboys vs Las Vegas Raiders — SPORT: NFL — FORMAT: FIVE_BLOCK  

_State: Q2 5:12, DAL 10 – LV 7, DAL ball, 2nd & 5 at LV 35._

**Block 1 – Final Prediction (Live)**

- Predicted final: Cowboys 27 – Raiders 20.  
- Live win probabilities: DAL ~64%, LV ~36%.  
- DAL still projected to control the game, but current drive state introduces short-term volatility.

Model vs App:
- Model ML: DAL ~64%, LV ~36%  
- App ML (example): DAL ~60%, LV ~40%  
- Comment: Model slightly more bullish on DAL due to field position and drive leverage; app more conservative.

**Block 2 – Model Breakdown (Live State)**

- Rating Model: Same as pregame; DAL remain a tier above LV.  
- Market/Odds Model: Live market keeps DAL as a one-score favorite.  
- Efficiency Model: DAL offense has moved the ball reasonably well; LV defense bending but not breaking.  
- Context Model: Mid–2nd quarter, DAL driving in plus territory with all timeouts.

**Block 3 – Context & Schedule (Live)**

- No major in-game injuries reported.  
- Both teams on standard rest; weather neutral.  
- This drive has above-average leverage for DAL cover chances.

**Block 4 – Agreement/Disagreement & Edge**

- Ratings and Efficiency continue to lean DAL.  
- Live market is slightly more punt-heavy on this drive than the model; both agree DAL are more likely to score than to go three-and-out.

**Block 5 – Sanity Check & Risk**

- A turnover or stalled red-zone trip here could quickly tighten live win and cover probabilities.  
- Explosive LV response drives remain the main upset path.

---

### LIVE DRIVE OVERLAY – CURRENT POSSESSION (FOOTBALL)

- State: Q2 5:12, DAL 10 – LV 7, DAL ball, 2nd & 5 at LV 35, timeouts DAL 3, LV 3.  

Model (drive-state):
- P(TD) ~28%  
- P(FG result) ~32%  
- P(Punt) ~25%  
- P(Turnover/Downs/Safety) ~15%  
- EP ≈ 2.7  

App/Market (example, mapped from “Drive Result” menu):
- P(TD) ~25%  
- P(FG result) ~30%  
- P(Punt) ~30%  
- P(Turnover/Downs/Safety) ~15%  

Comment:
- Market slightly more punt-heavy than the model from this field position, but both view DAL as more likely to produce points than to have a scoreless drive; this drive meaningfully affects DAL -X.5 cover prospects.

---

**RUN SUMMARY – QUICK VIEW**

2A. Dallas Cowboys vs Las Vegas Raiders (NFL, live) → DAL 27 – LV 20, DAL win ~64%

**RUN SUMMARY – SCORING BY PERIOD**

2A. Dallas Cowboys vs Las Vegas Raiders  
   - End Q1: DAL 7 – LV 3  
   - Halftime (updated): DAL 13 – LV 10  
   - End Q3: DAL 20 – LV 13  
   - Final: DAL 27 – LV 20  ← Q4 still expected to be the most decisive quarter  

---

## 3. Soccer Example (Pre-Game)

### Game Output

GAME: Spain vs Turkiye — SPORT: SOCCER — FORMAT: FOUR_BLOCK

**Block 1 – Final Prediction**

- Predicted final: Spain 2 – Turkiye 1.  
- Probabilities: P(Spain) ~54%, P(Draw) ~26%, P(Turkiye) ~20%.  
- Spain’s superior squad depth and xG profile give them an edge, but Turkiye remains dangerous on counters and set pieces.

**Block 2 – Model Breakdown**

- Rating Model: Spain clearly ahead on team strength and league pedigree.  
- xG / Chance Creation Model: Spain creates more consistent chances; Turkiye relies more on direct attacks.  
- Form & Schedule Model: Spain in solid form but with mild fixture congestion; Turkiye less consistent but fresher.

**Block 3 – Context & Match Dynamics**

- Crowd likely leaning toward Spain, even if not a pure home match.  
- Tactical expectation: Spain dominating possession, Turkiye defending deep and countering.  
- No catastrophic lineup news; some rotation possible.

**Block 4 – Upset Risk, Draw Likelihood & Sanity Check**

- Draw fairly live given Turkiye’s set-piece threat and defensive posture.  
- One early red card or penalty could completely change the match flow.  
- Penalties or extra time are not modeled unless explicitly requested.

---

### Run Summary Sections (Soccer)

**RUN SUMMARY – QUICK VIEW**

3. Spain vs Turkiye (SOCCER) → ESP 2 – TUR 1, P(ESP) ~54%, Draw ~26%, P(TUR) ~20%

**RUN SUMMARY – SCORING BY PERIOD**

3. Spain vs Turkiye  
   - Halftime: ESP 1 – TUR 0  
   - Final: ESP 2 – TUR 1  ← second half expected to be more open and higher scoring  

---

## 3A. Soccer Example with TWO_WAY_VALUE_DUTCH (Analytic Overlay)

### Game Output

GAME: Brighton vs Brentford — SPORT: SOCCER — FORMAT: FOUR_BLOCK

**Block 1 – Final Prediction**

- Predicted final: Brighton 2 – Brentford 1.  
- Model probabilities: P(Brighton) ~47%, P(Draw) ~25%, P(Brentford) ~28%.  
- Brighton’s possession and chance-creation edge make them slight favorites; Brentford remain live on counters and set pieces.

**Block 2 – Model Breakdown**

- Rating Model: Brighton slightly higher-rated over the season.  
- xG / Chance Creation: Brighton generate more consistent volume; Brentford have efficient shot quality.  
- Form & Schedule: Both mid-table form; Brighton mildly more stable.

**Block 3 – Context & Match Dynamics**

- Brighton at home, expected to dominate the ball.  
- Brentford likely to defend deep and strike on counters and set pieces.  
- No extreme weather or pitch concerns.

**Block 4 – Upset Risk, Draw Likelihood & Sanity Check**

- Draw fairly live if Brighton’s finishing lapses or Brentford hold firm in the box.  
- Brentford win path: early goal, then low-block game script or late set-piece swing.

---

### Advanced Overlay – TWO_WAY_VALUE_DUTCH (Concept Only)

Model vs Market (illustrative):

- Model: H/D/A = 47% / 25% / 28%  
- Market (de-vigged): H/D/A ≈ 44% / 30% / 26%  

Observations:

- P(Brighton)_model > P(Brighton)_market  
- P(Brentford)_model > P(Brentford)_market  
- P(Draw)_model < P(Draw)_market  

This is a **TWO_WAY_VALUE_DUTCH** pattern in analytical terms:

> Both non-draw outcomes (Brighton or Brentford) appear underpriced vs the model, while Draw appears slightly overpriced.  
> This statement is purely about probabilities; no staking or trade guidance is implied.

---

### Run Summary Sections (with Overlay)

**RUN SUMMARY – QUICK VIEW**

3A. Brighton vs Brentford (SOCCER) → BHA 2 – BRE 1, P(BHA) ~47%, Draw ~25%, P(BRE) ~28%

**RUN SUMMARY – SCORING BY PERIOD**

3A. Brighton vs Brentford  
   - Halftime: BHA 1 – BRE 1  
   - Final: BHA 2 – BRE 1  ← second half expected to produce the deciding goal  

**RUN SUMMARY – ADVANCED OVERLAY**

3A. Brighton vs Brentford (SOCCER) → Overlay: TWO_WAY_VALUE_DUTCH; both win sides (Brighton/Brentford) show positive model edge vs market, draw appears slightly rich.

---

## 4. Tennis Example

### Match Output

GAME: Alcaraz vs Sinner — SPORT: TENNIS — FORMAT: FIVE_BLOCK

**Block 1 – Final Prediction**

- Predicted final: Alcaraz wins 2 sets to 1.  
- Win probabilities: Alcaraz ~60%, Sinner ~40%.  
- Alcaraz’s slight rating edge on hard court and stronger return numbers give him a narrow advantage.

**Block 2 – Model Breakdown**

- Rating Model: Alcaraz rated slightly higher overall and on hard courts.  
- Serve/Return Model: Both serve well; Alcaraz holds a small edge in return points won, especially on second serve.  
- Market/Odds Model: Books shade Alcaraz as a modest favorite, broadly aligning with the ratings.  
- Context Model: Both in good form; no obvious injury red flags.

**Block 3 – Context & Match Dynamics**

- Surface: medium-paced hard court rewarding aggressive baseliners.  
- Expected script: long rallies with occasional explosive winners from both sides.  
- Tiebreak likely in at least one set given serve quality.

**Block 4 – Agreement/Disagreement & Edge**

- Ratings, serve/return data, and market all marginally favor Alcaraz.  
- Sinner’s path lies in sustained serving dominance and forcing Alcaraz into defensive positions.

**Block 5 – Sanity Check & Risk**

- One or two poor service games from Alcaraz could flip the match.  
- Best-of-three format keeps variance high; a coin-flip tiebreak or minor injury swing matters a lot.  
- This is a competitive matchup; edges are real but thin.

---

### Run Summary Sections (Tennis)

**RUN SUMMARY – QUICK VIEW**

4. Alcaraz vs Sinner (TENNIS) → ALC 2 sets – SIN 1 set, ALC win ~60%

**RUN SUMMARY – SCORING BY PERIOD**

4. Alcaraz vs Sinner  
   - After Set 1: ALC 1 – SIN 0  
   - After Set 2: ALC 1 – SIN 1  
   - After Set 3: ALC 2 – SIN 1 (Final)  ← deciding set expected to be tight but decisive  

---

## 5. Baseball Example

### Game Output

GAME: Yankees @ Red Sox — SPORT: BASEBALL — FORMAT: FIVE_BLOCK

**Block 1 – Final Prediction**

- Predicted final: Yankees 5 – Red Sox 4.  
- Win probabilities: NYY ~55%, BOS ~45%.  
- Slight offensive edge for the Yankees and a small starting-pitching advantage tilt a close game their way.

**Block 2 – Model Breakdown**

- Rating / Run Environment Model: Yankees graded marginally higher overall; Fenway is a hitter-friendly park.  
- Efficiency Model: Yankees’ lineup carries stronger wRC+ and more power; Red Sox closer on OBP.  
- Market/Odds Model: Moneyline prices show Yankees as a modest road favorite, consistent with model view.  
- Context Model: Both bullpens used moderately the night before; weather favors hitters with mild temps and light tailwind.

**Block 3 – Context & Game Flow**

- Expect runs in the middle innings as both lineups see the starters multiple times.  
- Late-inning leverage tilts slightly toward the team with fresher high-leverage relievers, currently Yankees.  
- Extra-inning chaos possible if late scoring ties the game.

**Block 4 – Agreement/Disagreement & Edge**

- All models lean Yankees, but by small margins; most likely outcome band is close games decided by 1–2 runs.  
- Red Sox upset path centers on early HRs off the Yankees starter or a bullpen meltdown.

**Block 5 – Sanity Check & Risk**

- A single bad inning can blow any baseball forecast apart.  
- Late scratches in the lineup or starting-pitcher changes require a fresh look.  
- Treat this as a modest lean, not a strong conviction.

---

### Run Summary Sections (Baseball)

**RUN SUMMARY – QUICK VIEW**

5. Yankees @ Red Sox (BASEBALL) → NYY 5 – BOS 4, NYY win ~55%

**RUN SUMMARY – SCORING BY PERIOD**

5. Yankees @ Red Sox  
   - End 3rd: NYY 1 – BOS 1  
   - End 6th: NYY 3 – BOS 3  
   - Final (End 9th): NYY 5 – BOS 4  ← middle-to-late innings expected to see the most scoring clusters  

---

## 6. Golf Example

### Tournament & Matchup Output

GAME: Masters Outrights (Scheffler, McIlroy, Rahm) — SPORT: GOLF — FORMAT: FOUR_BLOCK

**Block 1 – Final Prediction**

- Scheffler rated primary favorite with win ~14%, top-5 ~45%, top-10 ~70%.  
- McIlroy and Rahm in the next tier with win probabilities in the high single to low double digits.  
- All three project as serious contenders on this layout.

**Block 2 – Model Breakdown**

- SG Ability: Scheffler’s tee-to-green numbers outpace most of the field; Rahm close behind, McIlroy elite off the tee.  
- Course Fit: All three have strong histories or profiles for Augusta-style shot shaping and green complexes.  
- Form & Volatility: Scheffler’s recent finishes show elite consistency; McIlroy higher volatility but massive ceiling.

**Block 3 – Context & Setup**

- Course expected to play firm with fast greens, rewarding precise approach play and imaginative short game.  
- Weather moderate; no severe wind or storms forecast in early rounds.  
- Field strength extremely high; even strong favorites have modest absolute win percentages.

**Block 4 – Upside, Volatility & Sanity Check**

- Golf variance means even top players can miss the cut or drift out of contention with one bad round.  
- Hot putting weeks from less-heralded players can produce surprises.  
- Treat these as directional viewpoints rather than precise guarantees.

---

GAME: Scheffler vs McIlroy – Round 1 matchup, Augusta — SPORT: GOLF — FORMAT: FOUR_BLOCK

**Block 1 – Final Prediction**

- Predicted R1 scores: Scheffler 69, McIlroy 70.  
- Probability Scheffler posts the lower score: ~58%.  
- Edge driven by slightly stronger recent approach play and Augusta comfort.

**Block 2 – Model Breakdown**

- Ability: Scheffler’s tee-to-green trend better in recent events; McIlroy gains more off the tee.  
- Course Fit: Both elite fits; Scheffler’s Augusta record slightly more stable.  
- Form & Volatility: McIlroy’s round-to-round variance higher, increasing spread of outcomes.

**Block 3 – Context & Setup**

- Early tee times with relatively calm winds expected.  
- Greens likely to firm up over the day, making morning wave slightly advantageous.

**Block 4 – Upside, Volatility & Sanity Check**

- One poor wedge or short-game stretch can quickly flip a one-stroke projection.  
- Putting noise over 18 holes is enormous; consider the matchup modestly lean rather than strong.

---

### Run Summary Sections (Golf)

**RUN SUMMARY – QUICK VIEW**

6. Masters Outrights (GOLF) → Scheffler primary favorite (win ~14%, top-5 ~45%, top-10 ~70%; McIlroy/Rahm close tier)  
7. Scheffler vs McIlroy – R1 (GOLF) → Scheffler 69 – McIlroy 70, Scheffler lower score ~58%

**RUN SUMMARY – SCORING BY PERIOD**

6. Masters Outrights  
   - End R1: Scheffler projected around −3 relative to par (leaderboard bunched)  
   - End R2: Scheffler projected firmly inside top 10  
   - End R3: Scheffler projected in or near final groups  
   - Final (End R4): Scheffler finishes in the top-10 with non-trivial win equity  ← R3 expected as “moving day”  

7. Scheffler vs McIlroy – R1  
   - End Front 9: Scheffler −2, McIlroy −1  
   - Final (18): Scheffler −3, McIlroy −2  ← back nine slightly more volatile with key scoring holes  

---


## 7. V5 Example — World Cup Match with the Confidence Layer

GAME: Argentina vs Morocco — SPORT: SOCCER — FORMAT: FOUR_BLOCK

**Block 1 – Final Prediction**
- Predicted final: Argentina 2 – Morocco 1.
- Probabilities: P(ARG) ~58%, Draw ~24%, P(MAR) ~18%.
- Argentina's Elo edge and chance-creation depth outweigh Morocco's block-and-counter structure, but knockout draw rates keep the middle outcome live.
- Model vs Market: model P(ARG) ~58% vs market ~55% after de-vig; modest positive delta on ARG.
- Confidence: B — reason codes: fresh distillate (as-of today), full squads confirmed, small knockout sample vs this opponent type.

**Block 2 – Model Breakdown**
- Rating: ARG Elo 2113 (#2) vs MAR (top-15) — clear but not overwhelming gap.
- xG/Chance Creation: ARG stronger sustained creation; MAR elite defensive compactness, transition threat real.
- Form & Schedule: both advanced without extra time; equal rest.
- Data as-of 2026-07-05 (results through 2026-07-04).

**Block 3 – Context & Match Dynamics**
- Knockout round: draw at 90′ goes to extra time — state which basis probabilities use (here: 90-minute result for H/D/A; advancement probabilities quoted separately).
- Heat/travel per NA venue schedule; MAR's low block raises set-piece leverage.

**Block 4 – Upset Risk, Draw Likelihood & Sanity Check**
- MAR path: clean sheet past 60′, set piece or transition goal.
- Tripwires:
  - ARG confirms 3+ rotations at lineup release -> re-run before kickoff
  - MAR starting GK ruled out -> shift ~2% ARG-ward, confidence to B+
  - Kickoff temp >32C -> raise draw-at-90′ weight one notch

**RUN SUMMARY – QUICK VIEW**
1. Argentina vs Morocco (SOCCER) → ARG 2 – MAR 1, P(ARG) ~58%, Draw ~24%, P(MAR) ~18% (Conf B)

**RUN SUMMARY – SCORING BY PERIOD**
1. Argentina vs Morocco
   - Halftime: ARG 1 – MAR 0
   - Final: ARG 2 – MAR 1  ← second half expected more open as MAR chases

## 8. V5 Example — POST_GAME_REVIEW

Input: "Grade it: Argentina 1 – Morocco 1 (ARG advanced on pens). We had ARG 2–1, 58/24/18, Conf B."

Output shape:
- Outcome vs prediction: 90′ result Draw (predicted ARG win); scoreline missed; advancement leg correct. Row Brier (3-way): (0.58-0)² + (0.24-1)² + (0.18-0)² = 0.947 — poor on the 90′ leg.
- Miss classification: VARIANCE leaning TACTICAL_SURPRISE — MAR's second-half shape change limited ARG to 0.4 xG after 60′; within stated draw risk (24%) but the mechanism was under-weighted.
- Update recommendation: watch — if knockout draws keep landing above modeled rate over next 5, raise draw prior one notch in the WC pack.

POSTMORTEM ROWS
D-014,2026-07-05,SOCCER,ARG_MAR_WC_R16,PREDICT_GAMES,"ARG win 90'","ARG 2-1; 58/24/18",0.58,0.55,B,"Elo edge; creation depth","MAR low block; pens","logged pre-match",Calen,pre-game,"90' result",DRAW 1-1 (ARG pens),VARIANCE/TACTICAL_SURPRISE,watch,"draw prior review at N5"

_End of Sample Predictions Playbook v5_
