# Source Registry (Stats, News & Market Context) – v5

This registry defines which public sources the Sports GPT should prefer when browsing for stats, standings, injuries, context, and market reference data.

---

## 1. Global Rules

1. **Priority**
   - Prefer official league/tour sites and long-standing stats providers.
   - Use reputable news outlets for injuries, lineups, and context.
   - Treat social media, random blogs, and tabloids as low-trust.
   - Treat sportsbooks, exchanges, and prediction markets (including Kalshi-style markets) as **market views** only – useful for implied probabilities and calibration, not ground truth about team strength.

2. **Conflicting data**
   - When credible sources disagree:
     - Prefer sources with transparent methodology or official status.
     - Mention the conflict briefly in the Sanity Check / Risk block.

3. **Usage**
   - This registry guides **where to browse**, not fixed numbers.
   - The assistant should still reason and avoid over-anchoring on any single datapoint.
   - When using market/app sources (sportsbooks, prediction markets, live win% tiles, etc.):
     - Use them to infer **market-implied probabilities**.
     - Compare those to the model’s probabilities as part of the “Model vs App/Market” layer.
     - Never treat market prices as instructions for staking or trading.

---

## 2. NFL / College Football

**Primary stats & historical data**

- Pro-Football-Reference-style sites (game logs, team stats).
- Official league and team pages for box scores and basic stats.

**Advanced metrics**

- Reputable analytics sites that provide EPA/play, success rate, and other efficiency metrics.

**Injuries & depth charts**

- Official team sites.
- Established sports news outlets and beat reporters.

**Market context**

- Odds aggregators and large, established sportsbooks for spreads, totals, and moneylines.
- Prediction markets (e.g., Kalshi) and live app win% tiles when available:
  - Use for implied probabilities and for comparing the model to the market in real time.
  - Treat each contract description as a definition of a joint event; use your own model to estimate its probability.

---

## 3. NBA / College Basketball

**Primary stats**

- Basketball-reference-style databases.
- Official NBA/league stats sites for advanced metrics.

**Advanced analytics**

- Trusted analytics platforms providing Net Rating, on/off splits, tempo metrics, and shot-quality models for pro and college.

**Injuries & lineups**

- Team sites and established news outlets.

**Market context**

- Odds aggregators and reputable sportsbooks.
- Prediction markets and app-based live win% feeds as references for how the market is pricing the game at a given state.

---

## 4. NHL Hockey

**Primary stats**

- Natural Stat Trick–type sites for xG, Corsi, game logs.
- Hockey-reference-style databases for historical and advanced stats.

**Advanced analytics**

- Sites providing xG models, goalie GSAX, and detailed possession metrics.

**Injuries & goalie confirmations**

- Team sites and trusted beat reporters.

**Market context**

- Odds aggregators and mainstream sportsbooks.
- Prediction markets and live app win% tiles:
  - Use these to benchmark the model’s live win probabilities (e.g., one-goal game in the 3rd).
  - Do not treat them as overrides for your own model.

---

## 5. Soccer

**Primary stats**

- FBref/StatsBomb-style sources for xG and advanced stats.
- Understat-style sources when available for detailed xG by league.

**Fixtures & lineups**

- Official league and club sites.

**News & injuries**

- Major reputable sports news outlets and club communications.

**Market context**

- Odds aggregators and mainstream sportsbooks for 1X2, totals, and props.
- Prediction markets and live app tiles (e.g., P(Home/Draw/Away)):
  - Use to derive de-vigged market probabilities.
  - Compare model H/D/A probabilities to market as part of the TWO_WAY_VALUE_DUTCH and model-vs-market layers.

---

## 6. Tennis

**Primary stats & ratings**

- Official ATP/WTA/ITF sites for match results, rankings, and basic stats.
- Well-established tennis analytics sites for surface-specific Elo or similar ratings.

**Serve/return metrics**

- Databases that track serve points won, return points won, tiebreak records, and hold/break rates.

**Injuries & withdrawals**

- Tournament communications and official player updates.
- Trusted tennis journalists and major sports outlets.

**Market context**

- Established sportsbooks and odds aggregators for match prices, setlines, and outrights.
- Prediction markets where available:
  - Use for implied match and set probabilities; compare to the rating + serve/return model.

---

## 7. Baseball

**Primary stats**

- Baseball-reference-style databases for box scores and historical stats.
- Official league sites for game logs and standings.

**Advanced analytics**

- Reputable sabermetric platforms providing wRC+, wOBA, FIP/xFIP/SIERA, park factors, and platoon splits.

**Injuries & lineups**

- Team sites and beat reporters for lineups and pitcher confirmations.

**Market context**

- Odds aggregators and mainstream sportsbooks for moneylines, runlines, and totals.
- Prediction markets where available (for series or games) as a check against the model’s win probabilities.

---

## 8. Golf

**Primary stats**

- Official tour sites (PGA, DP World Tour, LPGA, etc.) for fields, scores, and basic stats.
- Advanced analytics providers that publish strokes-gained and course-fit data.

**Tournaments & course info**

- Event pages for course yardage, par, and setup details.
- Reliable preview articles for context on course difficulty, expected scoring, and wind/wave effects.

**Weather & tee times**

- Standard weather services for wind, temperature, and precipitation.
- Tour tee-time sheets to identify wave effects.

**Market context**

- Odds aggregators and mainstream sportsbooks for outrights, placements, and matchups.
- Prediction markets for tournament winner / finishing position when available:
  - Use for implied win/top-X probabilities and to benchmark model SG-based projections.

---

## 9. Scoring Distribution Guidance for Run Summary

When building **RUN SUMMARY – SCORING BY PERIOD**:

1. Use the final predicted score or finishing expectation from Block 1 as the total scoring anchor.
2. Distribute scoring across segments using:
   - Heuristics from the Metrics & Concepts Glossary.
   - Any period-by-period, set-level, inning-level, or round-level splits available from the above sources.
3. If detailed segment data is unavailable, use realistic generic patterns instead of pretending to know exact splits.
4. If assumptions are especially speculative, state that briefly in the Sanity Check / Risk block.
5. For golf:
   - When giving round-level expectations, keep differences modest and acknowledge volatility.
6. For tennis:
   - Ensure set-level expectations (who leads after Set 1/2/3) are consistent with the overall match prediction.
7. For baseball:
   - Avoid forecasting multiple huge innings unless the total run environment justifies it.

---

## 10. Market / App Snapshots for Live Calibration

When the user provides screenshots from apps or exchanges that show live win percentages or contract prices:

- Treat them as **market context sources**:
  - Derive implied probabilities.
  - Compare to the model’s probabilities as part of Block 1 or Block 4 (“Model vs App/Market”).
- For structured contracts (e.g., Kalshi):
  - Use the contract description as the definition of the event.
  - Use prices only to infer the market’s implied probability.
- Never treat these sources as prescriptive for what the user should trade or how; they are always benchmarks, not instructions.

---


## 11. V5 — Sports Intel Spine (PRIMARY source for rolling team data)

The GitHub data spine (`sports-intel-spine` repo, reached via the GPT Action) now outranks browsing for Tier-2 rolling data in covered sports.

**Call policy**
- One `getSoccerTeamProfiles` call per soccer run — the payload covers every team on the slate.
- `getWorldCupBaseRates` when World Cup context matters; `getSoccerDataVintage` only when staleness is suspected.
- Never call the Action for what knowledge files already hold (doctrine, ontology, static base rates).
- Echo `as_of` in Block 2 whenever Action data is used. On Action failure: proceed (knowledge + user data + browsing) and apply the FEED_DOWN confidence penalty.

**Source reliability grades (SIA-02, applies to ALL sources in this registry)**
- A — Direct/verified (official, repeatable measurement)
- B — Multi-source consistent (spine distillates; established stats providers)
- C — Plausible but limited (single reputable report; screenshots)
- D — Unverified (aggregators, unconfirmed beat reports)
- F — Rumor (never drives a conclusion; caps confidence at C when material)

Sports without spine coverage yet (until their packs ship): browse per sections 2–8 above, exactly as V4.

_End of Source Registry v5_
