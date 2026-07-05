"""Distill raw international soccer results into GPT-ready JSON.

Inputs  (data/soccer/raw/): results.csv (required), elo.csv (optional), shootouts.csv (optional)
Outputs (distillates/soccer/): team_profiles.json, wc_base_rates.json, meta.json

Design: compute at refresh time, not chat time. Outputs stay small and flat (SIA-02: every
payload carries provenance; the GPT echoes as_of in its output).
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "soccer" / "raw"
OUT = ROOT / "distillates" / "soccer"
WINDOW_YEARS = 4
LAST_N_WC = 5


def load_results() -> pd.DataFrame:
    df = pd.read_csv(RAW / "results.csv", parse_dates=["date"])
    df = df.dropna(subset=["home_score", "away_score"]).copy()
    df["home_score"] = df["home_score"].astype(int)
    df["away_score"] = df["away_score"].astype(int)
    return df


def team_rows(df: pd.DataFrame) -> pd.DataFrame:
    home = pd.DataFrame({
        "date": df["date"], "team": df["home_team"], "opp": df["away_team"],
        "gf": df["home_score"], "ga": df["away_score"],
        "tournament": df["tournament"], "neutral": df["neutral"],
    })
    away = pd.DataFrame({
        "date": df["date"], "team": df["away_team"], "opp": df["home_team"],
        "gf": df["away_score"], "ga": df["home_score"],
        "tournament": df["tournament"], "neutral": df["neutral"],
    })
    rows = pd.concat([home, away], ignore_index=True)
    rows["res"] = "D"
    rows.loc[rows.gf > rows.ga, "res"] = "W"
    rows.loc[rows.gf < rows.ga, "res"] = "L"
    return rows


def load_elo() -> dict:
    p = RAW / "elo.csv"
    if not p.exists():
        return {}
    try:
        e = pd.read_csv(p)
        cols = {c.lower().strip(): c for c in e.columns}
        team_c, rating_c = cols.get("team"), cols.get("rating")
        rank_c = cols.get("rank")
        if not team_c or not rating_c:
            return {}
        out = {}
        for _, r in e.iterrows():
            out[str(r[team_c]).strip()] = {
                "elo": round(float(r[rating_c])),
                "elo_rank": int(r[rank_c]) if rank_c and pd.notna(r[rank_c]) else None,
            }
        return out
    except Exception:
        return {}


def build_profiles(rows: pd.DataFrame, elo: dict, cutoff) -> dict:
    recent = rows[rows.date >= cutoff]
    teams = {}
    for team, g in recent.groupby("team"):
        g = g.sort_values("date")
        comp = g[g.tournament != "Friendly"]
        last10 = g.tail(10)["res"].tolist()
        teams[team] = {
            "gp": len(g),
            "w": int((g.res == "W").sum()), "d": int((g.res == "D").sum()), "l": int((g.res == "L").sum()),
            "gf_pg": round(g.gf.mean(), 2), "ga_pg": round(g.ga.mean(), 2),
            "comp_gp": len(comp),
            "comp_w_rate": round((comp.res == "W").mean(), 3) if len(comp) else None,
            "last10": "".join(last10),
            "elo": elo.get(team, {}).get("elo"),
            "elo_rank": elo.get(team, {}).get("elo_rank"),
        }
    return teams


def wc_slice_stats(wc: pd.DataFrame) -> dict:
    n = len(wc)
    if n == 0:
        return {}
    goals = wc.home_score + wc.away_score
    return {
        "games": n,
        "draw_rate_ft": round((wc.home_score == wc.away_score).mean(), 3),
        "avg_goals": round(goals.mean(), 2),
        "goals_le_1_rate": round((goals <= 1).mean(), 3),
        "goals_ge_4_rate": round((goals >= 4).mean(), 3),
        "designated_home_w_rate": round((wc.home_score > wc.away_score).mean(), 3),
    }


def build_wc_base_rates(df: pd.DataFrame) -> dict:
    wc = df[df.tournament == "FIFA World Cup"].copy()
    if wc.empty:
        return {"note": "no FIFA World Cup rows found - check source"}
    wc["year"] = wc.date.dt.year
    years = sorted(wc.year.unique())
    last_editions = years[-LAST_N_WC:]
    return {
        "all_time": wc_slice_stats(wc),
        f"last_{len(last_editions)}_editions": wc_slice_stats(wc[wc.year.isin(last_editions)]),
        "editions_included": [int(y) for y in years],
        "caveats": [
            "Scores may include extra time for knockout games; treat draw_rate_ft as approximate",
            "Most WC games are neutral-venue; designated_home_w_rate is not a true home-advantage measure",
        ],
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = load_results()
    as_of = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    latest = df.date.max()
    cutoff = latest - pd.DateOffset(years=WINDOW_YEARS)
    elo = load_elo()

    profiles = {
        "as_of": as_of,
        "data_through": latest.strftime("%Y-%m-%d"),
        "window_years": WINDOW_YEARS,
        "elo_loaded": bool(elo),
        "teams": build_profiles(team_rows(df), elo, cutoff),
    }
    base_rates = {"as_of": as_of, **build_wc_base_rates(df)}
    meta = {
        "as_of": as_of,
        "source": "github.com/martj42/international_results",
        "rows_total": int(len(df)),
        "data_through": latest.strftime("%Y-%m-%d"),
        "teams_profiled": len(profiles["teams"]),
        "elo_loaded": bool(elo),
        "sia_note": "If data_through lags today by >7 days in-tournament, apply SIA-02 staleness confidence penalty",
    }

    (OUT / "team_profiles.json").write_text(json.dumps(profiles, separators=(",", ":")), encoding="utf-8")
    (OUT / "wc_base_rates.json").write_text(json.dumps(base_rates, indent=1), encoding="utf-8")
    (OUT / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    sample = OUT / "SAMPLE_team_profiles.json"
    if sample.exists():
        sample.unlink()
    print(f"distilled {meta['teams_profiled']} teams; data through {meta['data_through']}")


if __name__ == "__main__":
    main()
