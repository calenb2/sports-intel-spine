"""Distill CFB results (api.collegefootballdata.com) into GPT-ready JSON.

Requires env CFBD_API_KEY (repo secret). v1 scope: FBS results-based
profiles + simple Elo over last two completed seasons.

Outputs (distillates/cfb/): team_profiles.json, meta.json
"""
import json
import os
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "distillates" / "cfb"
ELO_K = 24.0
ELO_HFA = 55.0
ELO_START = 1500.0


def api(path: str, key: str):
    req = urllib.request.Request(
        f"https://api.collegefootballdata.com{path}",
        headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)


def fetch_games(season: int, key: str) -> list:
    rows = api(f"/games?year={season}&seasonType=both&division=fbs", key)
    games = []
    for g in rows:
        hp, ap = g.get("homePoints"), g.get("awayPoints")
        # tolerate snake_case variants across API versions
        if hp is None:
            hp = g.get("home_points")
        if ap is None:
            ap = g.get("away_points")
        if hp is None or ap is None:
            continue
        games.append({
            "date": (g.get("startDate") or g.get("start_date") or "")[:10],
            "season": season,
            "home": g.get("homeTeam") or g.get("home_team"),
            "away": g.get("awayTeam") or g.get("away_team"),
            "hs": int(hp), "as_": int(ap),
        })
    return games


def run_elo(games: list) -> dict:
    elo: dict = {}
    for g in sorted(games, key=lambda x: (x["season"], x["date"])):
        h, a = g["home"], g["away"]
        eh, ea = elo.get(h, ELO_START), elo.get(a, ELO_START)
        exp_h = 1.0 / (1.0 + 10 ** (-((eh + ELO_HFA) - ea) / 400.0))
        res_h = 1.0 if g["hs"] > g["as_"] else 0.0
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
            p = teams.setdefault(t, {"gp": 0, "w": 0, "l": 0, "pf": 0, "pa": 0, "res": []})
            p["gp"] += 1
            p["pf"] += g[gf]
            p["pa"] += g[ga]
            won = g[gf] > g[ga]
            p["w" if won else "l"] += 1
            p["res"].append("W" if won else "L")
    out = {}
    for t, p in teams.items():
        out[t] = {
            "season": latest_season,
            "gp": p["gp"], "w": p["w"], "l": p["l"],
            "pf_pg": round(p["pf"] / p["gp"], 1), "pa_pg": round(p["pa"] / p["gp"], 1),
            "last10": "".join(p["res"][-10:]),
            "elo": elo.get(t), "elo_rank": rank.get(t),
        }
    return out


def main() -> None:
    key = os.environ.get("CFBD_API_KEY", "").strip()
    if not key:
        raise SystemExit("CFBD_API_KEY secret not set - add it in repo Settings > Secrets > Actions")
    OUT.mkdir(parents=True, exist_ok=True)
    latest_completed = date.today().year - 1 if date.today().month < 9 else date.today().year
    seasons = [latest_completed - 1, latest_completed]
    games: list = []
    for s in seasons:
        games.extend(fetch_games(s, key))
    if not games:
        raise SystemExit("no CFB games fetched - check key/tier")
    as_of = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    profiles = {
        "as_of": as_of,
        "data_through": max(g["date"] for g in games),
        "window_seasons": seasons,
        "elo_note": f"simple Elo k={ELO_K} hfa={ELO_HFA}; FBS; records/last10 from {latest_completed}",
        "teams": build_profiles(games, latest_completed),
    }
    meta = {
        "as_of": as_of, "source": "api.collegefootballdata.com /games",
        "games_total": len(games), "data_through": profiles["data_through"],
        "teams_profiled": len(profiles["teams"]),
        "sia_note": "Free-tier friendly: one bulk call per season, nightly in season only.",
    }
    (OUT / "team_profiles.json").write_text(json.dumps(profiles, separators=(",", ":")), encoding="utf-8")
    (OUT / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(f"distilled {meta['teams_profiled']} FBS teams from {len(games)} games; through {profiles['data_through']}")


if __name__ == "__main__":
    main()
