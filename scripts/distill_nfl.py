"""Distill NFL results (nflverse games data) into GPT-ready JSON.

v1 scope: results-based team profiles + simple Elo over last two completed
seasons. EPA/efficiency enrichment from play-by-play is R2.2.

Outputs (distillates/nfl/): team_profiles.json, meta.json
"""
import csv
import io
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "distillates" / "nfl"
SOURCES = [
    "https://github.com/nflverse/nflverse-data/releases/download/games/games.csv",
    "http://www.habitatring.com/games.csv",
]
ELO_K = 20.0
ELO_HFA = 48.0
ELO_START = 1500.0


def fetch_games() -> list:
    last_err = None
    for url in SOURCES:
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                text = r.read().decode("utf-8", errors="replace")
            rows = list(csv.DictReader(io.StringIO(text)))
            if rows:
                print(f"fetched {len(rows)} rows from {url}")
                return rows
        except Exception as e:  # try fallback
            last_err = e
    raise SystemExit(f"all NFL sources failed: {last_err}")


def completed(rows: list, seasons: set) -> list:
    out = []
    for g in rows:
        try:
            season = int(g["season"])
        except (KeyError, ValueError):
            continue
        if season not in seasons:
            continue
        hs, as_ = g.get("home_score", ""), g.get("away_score", "")
        if hs in ("", "NA", None) or as_ in ("", "NA", None):
            continue
        out.append({
            "date": g.get("gameday", ""), "season": season,
            "type": g.get("game_type", "REG"),
            "home": g["home_team"], "away": g["away_team"],
            "hs": int(float(hs)), "as_": int(float(as_)),
        })
    return out


def run_elo(games: list) -> dict:
    elo: dict = {}
    for g in sorted(games, key=lambda x: (x["season"], x["date"])):
        h, a = g["home"], g["away"]
        eh, ea = elo.get(h, ELO_START), elo.get(a, ELO_START)
        exp_h = 1.0 / (1.0 + 10 ** (-((eh + ELO_HFA) - ea) / 400.0))
        res_h = 1.0 if g["hs"] > g["as_"] else (0.5 if g["hs"] == g["as_"] else 0.0)
        elo[h] = eh + ELO_K * (res_h - exp_h)
        elo[a] = ea + ELO_K * ((1 - res_h) - (1 - exp_h))
    return {t: round(v) for t, v in elo.items()}


def build_profiles(games: list, latest_season: int) -> dict:
    elo = run_elo(games)
    rank = {t: i + 1 for i, (t, _) in enumerate(sorted(elo.items(), key=lambda x: -x[1]))}
    cur = [g for g in games if g["season"] == latest_season]
    teams: dict = {}
    for g in sorted(cur, key=lambda x: x["date"]):
        for side, gf, ga in (("home", "hs", "as_"), ("away", "as_", "hs")):
            t = g[side]
            p = teams.setdefault(t, {"gp": 0, "w": 0, "l": 0, "t": 0, "pf": 0, "pa": 0, "res": []})
            p["gp"] += 1
            p["pf"] += g[gf]
            p["pa"] += g[ga]
            r = "W" if g[gf] > g[ga] else ("T" if g[gf] == g[ga] else "L")
            p["w" if r == "W" else ("t" if r == "T" else "l")] += 1
            p["res"].append(r)
    out = {}
    for t, p in teams.items():
        out[t] = {
            "season": latest_season,
            "gp": p["gp"], "w": p["w"], "l": p["l"], "ties": p["t"],
            "pf_pg": round(p["pf"] / p["gp"], 1), "pa_pg": round(p["pa"] / p["gp"], 1),
            "last10": "".join(p["res"][-10:]),
            "elo": elo.get(t), "elo_rank": rank.get(t),
        }
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = fetch_games()
    seasons_available = {int(r["season"]) for r in rows if r.get("season", "").isdigit()}
    latest = max(s for s in seasons_available)
    # last two seasons with any completed games (handles offseason: latest completed season)
    window = {latest, latest - 1}
    games = completed(rows, window)
    if not games:
        window = {latest - 1, latest - 2}
        games = completed(rows, window)
    latest_completed = max(g["season"] for g in games)
    as_of = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    profiles = {
        "as_of": as_of,
        "data_through": max(g["date"] for g in games),
        "window_seasons": sorted(window),
        "elo_note": f"simple Elo k={ELO_K} hfa={ELO_HFA}; records/last10 from season {latest_completed}",
        "teams": build_profiles(games, latest_completed),
    }
    meta = {
        "as_of": as_of, "source": "nflverse games data",
        "games_total": len(games), "data_through": profiles["data_through"],
        "teams_profiled": len(profiles["teams"]),
        "sia_note": "Offseason: staleness window 30d. In season: 2d, nightly cron.",
    }
    (OUT / "team_profiles.json").write_text(json.dumps(profiles, separators=(",", ":")), encoding="utf-8")
    (OUT / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(f"distilled {meta['teams_profiled']} teams from {len(games)} games; through {meta['data_through']}")


if __name__ == "__main__":
    main()
