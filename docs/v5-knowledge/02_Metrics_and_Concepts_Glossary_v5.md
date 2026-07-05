# Metrics & Concepts Glossary (v5)

This glossary defines how the Sports GPT interprets key metrics and tempo concepts across sports, and how it talks about model vs market structure.

---

## 1. Football (NFL / CFB)

- **EPA/play (Expected Points Added per play)**  
  Change in expected points before vs after a play, averaged over plays. Accounts for down, distance, and field position.

- **Expected Points (EP)**  
  Baseline expected net points for the offense from a given down, distance, and field position (and, when needed, time context). The live drive layer uses EP tables as the backbone for drive result probabilities (TD / field-goal result / punt / turnover).

- **Success rate**  
  Percentage of plays that increase expected points (positive EPA). Often broken out by early downs vs late downs.

- **Yards per play (YPP)**  
  Average offensive yards gained per play. Basic but useful when combined with efficiency and explosiveness.

- **Explosive play rate**  
  Share of plays gaining large chunks (e.g., 15+ yard passes, 10+ yard runs).

- **Red-zone TD rate**  
  Percentage of red-zone drives ending in touchdowns.

- **Third-down conversion rate**  
  Success converting third downs (and fourth downs where relevant).

- **Turnover rate**  
  Turnovers per drive or per play. Major driver of variance.

- **Pace (seconds per play / plays per game)**  
  How fast an offense snaps the ball, impacting total plays and scoring environment.

---

## 2. Basketball (NBA / CBB)

- **Offensive Rating (ORtg)**  
  Points scored per 100 possessions.

- **Defensive Rating (DRtg)**  
  Points allowed per 100 possessions.

- **Net Rating**  
  ORtg − DRtg. Positive net rating indicates stronger overall performance.

- **Pace**  
  Estimated possessions per game (per 48 minutes in NBA, per 40 minutes in most college formats).

- **Effective Field Goal Percentage (eFG%)**  
  Shooting efficiency adjusted for 3-point attempts being worth more.

- **True Shooting Percentage (TS%)**  
  Efficiency including field goals and free throws.

- **Turnover Percentage (TOV%)**  
  Turnovers per 100 possessions.

- **Offensive / Defensive Rebound Percentage (ORB% / DRB%)**  
  Share of available rebounds secured on each end.

- **Free Throw Rate (FTr)**  
  Free throw attempts relative to field goal attempts; proxy for how often a team gets to the line.

---

## 3. Hockey (NHL)

- **Corsi**  
  Shot attempts for and against (shots on goal + missed + blocked) at 5v5. Proxy for possession and territory.

- **Fenwick**  
  Corsi excluding blocked shots. Slightly closer to shots that reach the net.

- **Expected Goals (xG)**  
  Shot-quality model estimating goal probability for each shot; summed for team-level xG.

- **High-Danger Chances**  
  Chances from high-probability scoring areas close to the net.

- **Power Play Percentage (PP%)**  
  Goals scored divided by power-play opportunities.

- **Penalty Kill Percentage (PK%)**  
  Percentage of opposition power plays successfully killed without conceding.

- **Save Percentage (SV%)**  
  Saves divided by shots on goal.

- **Goals Saved Above Expected (GSAX)**  
  Goals prevented versus what xG suggests an average goalie would allow.

- **Score effects**  
  Teams trailing often push more; teams leading often sit back. This shapes Corsi/xG without necessarily changing true talent.

---

## 4. Soccer

- **Expected Goals (xG)**  
  Chance quality measure; probability that each shot becomes a goal, summed over a team or player.

- **Expected Goals Against (xGA)**  
  Aggregate xG conceded.

- **Expected Goal Difference (xGD)**  
  xG − xGA. Positive xGD suggests stronger underlying performance than opponents.

- **Field tilt / Territory**  
  Share of touches, passes, or possessions in advanced zones.

- **Pressing intensity**  
  Often proxied by metrics like PPDA (passes allowed per defensive action). Lower PPDA → more aggressive pressing.

- **Fixture congestion**  
  Multiple matches in a short window, causing fatigue and rotation.

- **Game state**  
  Whether the team is leading, drawing, or trailing; strongly affects risk-taking and tactics.

- **Set-piece strength**  
  Output from corners and free kicks; often crucial in low-scoring matches.

---

## 5. Baseball

- **wOBA (Weighted On-Base Average)**  
  Rate stat weighting different offensive events (walks, singles, doubles, etc.) by run value.

- **wRC+ (Weighted Runs Created Plus)**  
  Overall offensive value relative to league average (100 = league average, 120 = 20% better).

- **OPS / OPS+**  
  On-base plus slugging; plus variant adjusted for park and league.

- **FIP / xFIP / SIERA**  
  Pitching metrics focusing on strikeouts, walks, and homers; attempt to isolate pitcher skill.

- **K% / BB%**  
  Strikeout and walk rates per batter faced.

- **HR/9**  
  Home runs allowed per nine innings.

- **GB% / FB% / LD%**  
  Ground-ball, fly-ball, and line-drive rates.

- **Park factor**  
  How hitter- or pitcher-friendly a stadium is relative to league average.

- **Run expectancy / RE24**  
  Expected runs from each base/out state; used for inning-level and game-level scoring models.

---

## 6. Tennis

- **Elo / surface-specific rating**  
  Player-strength rating; surface-specific variants adjust for hard, clay, grass, indoor.

- **Hold% / Break%**  
  Percentage of service games held and return games broken; often surface-adjusted.

- **First-serve in% / First-serve points won%**  
  Serve reliability and effectiveness.

- **Second-serve points won%**  
  Key vulnerability indicator; weak second-serve performance raises break risk.

- **Return points won%**  
  Measures return pressure; high values correlate with strong break potential.

- **Tiebreak frequency**  
  How often a player’s sets reach 6–6; indicates serve dominance and tight sets.

---

## 7. Golf

- **Strokes Gained (SG)**  
  Shot-level metric comparing a player’s performance to a baseline (field or tour average) from each lie/distance.

- **SG: Off the Tee (SG:OTT)**  
  Value added with the driver and long clubs off the tee.

- **SG: Approach (SG:APP)**  
  Value added on approach shots into greens.

- **SG: Around the Green (SG:ARG)**  
  Value added on chips and pitches around the green.

- **SG: Putting (SG:PUTT)**  
  Value added (or lost) on the greens.

- **Scoring Average**  
  Average strokes per round; usually course- and field-dependent.

- **Course fit indicators**  
  Performance on similar course lengths, par distributions, grass types, and green speeds.

- **Round-to-round volatility**  
  Standard deviation of scores; higher volatility → wider finishing range.

---

## 8. Scoring Distribution & Tempo Heuristics

These heuristics guide realistic period/segment scoring predictions and Run Summary “Scoring by Period” outputs.

### 8.1 Football (NFL / CFB)

- Q1 may be slightly lower scoring as teams feel each other out.
- Q2 and Q4 often see more scoring (two-minute drills, end-game urgency).
- Balanced games: modest scoring ramp from Q1 to Q4 unless context strongly suggests otherwise.

### 8.2 Basketball (NBA / CBB)

- Scoring is relatively even across quarters/halves.
- Small shifts by quarter are fine; massive outliers need contextual support (e.g., huge pace spikes, bench vs starters).

### 8.3 Hockey (NHL)

- Typical full-game goals: low compared to other sports.
- Common pattern:
  - P1: 0–2 total goals.
  - P2: 1–3 total goals.
  - P3: 0–2 total goals with possible empty-net goals late.
- Big 4+ goal periods are rare and should only be forecast with strong justification.

### 8.4 Soccer

- First halves are often lower scoring than second halves.
- Reasonable patterns:
  - 0–1 goals in first half, remaining goals in second half.
  - Very high-scoring halves are possible but should reflect expected total xG and tactics.

### 8.5 Baseball

- Runs often cluster in a few innings rather than being perfectly even.
- Early innings (1–3):
  - Modest scoring while starters settle in.
- Middle innings (4–6):
  - Higher chance of crooked numbers as hitters see pitchers multiple times.
- Late innings (7–9):
  - Can be quiet if bullpens are strong, or swing wildly with tired arms and leverage.
- Predicting one clearly “highest scoring” chunk (e.g., 4th–6th) is reasonable for Run Summary.

### 8.6 Tennis

- BO3 matches:
  - 2-set matches usually have one set slightly more lopsided and one closer.
  - 3-set matches often feature a middle set flip or decider with tighter games.
- BO5 matches:
  - Early sets can be exploratory; deciders tend to be more volatile.
- Games per set:
  - Typical competitive sets land in the 9–13 game range (e.g., 6–4, 7–5, 7–6).

### 8.7 Golf

- Round scoring is relatively stable within a course and setup:
  - Field clustered within a few strokes in benign conditions.
  - Wind and firmness widen the spread.
- Within an 18-hole round:
  - Par 5s and reachable par 4s carry more birdie potential.
- Across a 72-hole event:
  - Leaderboard reshuffles are common after R2 and R3; extreme wire-to-wire dominance is rare.

These heuristics are guidelines, not hard rules. Departures should be briefly justified in context or sanity-check blocks.

---

## 9. Advanced Overlay & Market Concepts

These concepts support the **Advanced Overlay** layer (optional third section after Run Summaries) and structured model-vs-market analysis. They are descriptive only and must never be turned into staking advice.

### 9.1 TWO_WAY_VALUE_DUTCH

Context: 3-way moneyline markets (Home / Draw / Away) – typically in soccer.

Given:

- Model probabilities:  
  - `p_home`, `p_draw`, `p_away` (sum ≈ 100%).
- De-vigged market probabilities:  
  - `q_home`, `q_draw`, `q_away`.

We say **TWO_WAY_VALUE_DUTCH** exists when:

- `p_home > q_home`
- `p_away > q_away`
- and usually `p_draw ≤ q_draw`

Interpretation:

> Both non-draw outcomes (Home and Away) appear underpriced versus the model, while Draw is not. Structurally, “any non-draw result” looks comparatively more attractive than the draw at current prices.

Usage:

- The GPT may:
  - Describe this in an `ADVANCED OVERLAY` line,
  - Explain which outcomes look richer vs thinner vs market in neutral terms.
- The GPT must **not**:
  - Suggest combining legs or staking on them.

---

### 9.2 LONGSHOT_LEG

Any single leg/outcome the model assigns **< 20%** probability.

Examples:

- A Draw in a lopsided soccer match where the model says P(Draw) ≈ 12%.
- An underdog ML with model p ≈ 15%.
- Extreme props (e.g., exact scorelines) with low model probability.

Usage:

- Label longshot legs internally or in commentary to avoid over-weighting isolated hits or misses.
- In evaluation, longshot performance should be tracked separately from core favorites.

---

### 9.3 KALSHI_CONTRACT / STRUCTURED_YES_NO

A **structured YES/NO** contract where “YES” is a joint event over multiple game conditions, for example:

- “Team A wins, Team A does **not** win by more than 14.5, and total points are > 34.5.”

The GPT must:

1. **Parse the contract** into logical legs, such as:
   - Team A wins.
   - Margin condition (e.g., margin ≤ 14).
   - Total condition (e.g., total ≥ 35).
   - Any additional qualifiers.

2. **Map each leg** to the game model:
   - Use scoreline distribution to approximate:
     - P(win),
     - P(margin band | win),
     - P(total band).

3. **Approximate the joint probability** of all legs occurring:
   - Use reasonable discretization of scores,
   - Make it clear that this is approximate, not an exact combinatorial integration.

4. **Compare to market’s implied probability**:
   - If the user supplies “32.2% chance” or a price, treat that as `q_contract`.
   - Report `p_contract` (model) vs `q_contract` (market) and label the contract as:
     - cheaper than model,
     - roughly fair,
     - or more expensive than model.

5. **Never**:
   - Provide explicit trade or staking recommendations,
   - Claim that a contract is “guaranteed value”.

---

### 9.4 MODEL_VS_MARKET_DELTA

For any outcome `i` (team, draw, total band, etc.):

- **Model probability**: `p_i`
- **Market probability (de-vigged)**: `q_i`
- **Delta**: `Δ_i = p_i – q_i`

Interpretation:

- `Δ_i > 0`: model sees outcome `i` as happening more often than market implies.
- `Δ_i < 0`: model sees outcome `i` as happening less often than market implies.

Usage:

- For live model vs app comparisons:
  - Show both probabilities and briefly explain `Δ` in a sentence or two.
- For advanced overlays:
  - Use sign and magnitude of `Δ` to identify structural patterns (e.g., consistent model optimism on trailing favorites).

Again: these are descriptive diagnostics for calibration and explanation – not direct instructions to buy or sell.

---


## 10. V5 Confidence & Availability Concepts

- **Availability probability** — estimated chance an athlete participates at expected workload (0–100%). Distinct from binary "available"; carries a source grade. (SIA-09)
- **Expected workload** — projected share of normal minutes/snaps/innings given restrictions. A confirmed starter on a 60% minutes cap is modeled as a partial absence.
- **Data vintage / as_of** — the date a distillate was built and the last date of underlying results. Vintage older than the sport's staleness window triggers confidence penalties.
- **Confidence factor (C)** — numeric mapping of the confidence grade (A≈0.9 … F≈0.2) used in the shrinkage blend.
- **Shrinkage blend** — final stated probability = C × model + (1−C) × de-vigged market. Low confidence collapses toward market rather than manufacturing edge. Without market data, widen stated uncertainty instead.
- **National-team Elo** — eloratings.net-style rating for international soccer; margin-, importance-, and venue-aware. Used as the Rating Model prior in the WC sport pack.

_End of Metrics & Concepts Glossary v5_
