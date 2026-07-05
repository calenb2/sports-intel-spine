# sports-intel-spine

Data spine for **Sports GPT Guru V5**. This repo is the single source of truth; the GPT holds a cached snapshot of the slow layer (knowledge files) and reads the rolling layer here via one Action call per run.

## Layout

```
.github/workflows/   refresh-soccer.yml — scheduled pull + distill + commit (self-maintaining)
scripts/             distill_soccer.py — raw CSVs -> compact JSON distillates
action/              openapi.yaml — paste into the GPT's Action config (replace OWNER)
data/<sport>/raw/    raw pulled data + MANIFEST.json provenance (SIA-02)
distillates/<sport>/ what the GPT actually reads: small, flat, pre-computed JSON
postmortem/          postmortem_log.csv — every prediction + outcome (the proprietary dataset)
sources/             SOURCES.csv — every method + data source with license notes
docs/                FLIP_TO_PRIVATE.md and operational notes
```

## Operating rules (from the SIA Method)

1. No dataset enters without a MANIFEST entry (source, license, pull date, caveats) — SIA-02.
2. Distillates carry `as_of`; the GPT must echo data vintage in its Ratings & Market block.
3. If a pull fails, the workflow keeps the last good distillate; the GPT applies a staleness confidence penalty rather than stalling.
4. Every prediction run appends to `postmortem/postmortem_log.csv`. No postmortem, no learning loop — SIA-15.

## First run

Actions tab → `refresh-soccer` → **Run workflow**. Verify `distillates/soccer/team_profiles.json`, `wc_base_rates.json`, and `meta.json` appear with a fresh commit.

## Rollout order

Soccer (live now) → NFL (nflverse, before September) → MLB → Tennis → NBA/CBB → NHL → CFB → Golf. One workflow + one distiller per sport; copy the soccer pattern.
