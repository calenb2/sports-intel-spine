"""Distill MLB results from statsapi.mlb.com into GPT-ready JSON.

v1 scope: results-based team profiles + simple Elo (2-season window).
Statcast enrichment (Savant aggregates) is R1.2 - not in this distiller.

Outputs (distillates/mlb/): team_profiles.json, meta.json
"""
import json
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "distillates" / "mlb"
SEASONS = [date.today().year - 1, date.today().year]
ELO_K = 4.0
ELO_HFA = 24.0
ELO_START = 1500.0


def fetch_season_games(season: int) -> list:
    url = (
        "https://statsapi.mlb.com/api/v1/schedule"
        f"?sportId=1&gameTypes=R,P&startDate={season}-03-01&endDate={season}-11-15"
    )
    with urllib.request.urlopen(url, timeout=60) as r:
        data = json.load(r)
    games = []
    for d in data.get("dates", []):
        for g in d.get("games", []):
            status = g.get("status", {}).get("codedGameState", "")
            if status != "F":
                continue
            home, away = g["teams"]["home"], g["teams"]["away"]
            if home.get("score") is None or away.get("score") is None:
                continue
            games.append({
                "date": d["date"],
                "home": home["team"]["name"], "away": away["team"]["name"],
                "hs": int(home["score"]), "as_": int(away["score"]),
                "type": g.get("gameType", "R"),
            })
    return games


def run_elo(games: list) -> dict:
    elo: dict = {}
    for g in sorted(games, key=lambda x: x["date"]):
        h, a = g["home"], g["away"]
        eh, ea = elo.get(h, ELO_START), elo.get(a, ELO_START)
        exp_h = 1.0 / (1.0 + 10 ** (-((eh + ELO_HFA) - ea) / 400.0))
        res_h = 1.0 if g["hs"] > g["as_"] else 0.0
        elo[h] = eh + ELO_K * (res_h - exp_h)
        elo[a] = ea + ELO_K * ((1 - res_h) - (1 - exp_h))
    return {t: round(v) for t, v in elo.items()}


def build_profiles(games: list, current_season: int) -> dict:
    cur = [g for g in games if g["date"].startswith(str(current_season))]
    elo = run_elo(games)
    rank = {t: i + 1 for i, (t, _) in enumerate(sorted(elo.items(), key=lambda x: -x[1]))}
    teams: dict = {}
    for g in sorted(cur, key=lambda x: x["date"]):
        for side, opp_side, gf, ga in (("home", "away", "hs", "as_"), ("away", "home", "as_", "hs")):
            t = g[side]
            p = teams.setdefault(t, {"gp": 0, "w": 0, "l": 0, "rs": 0, "ra": 0, "res": []})
            p["gp"] += 1
            p["rs"] += g[gf]
            p["ra"] += g[ga]
            won = g[gf] > g[ga]
            p["w" if won else "l"] += 1
            p["res"].append("W" if won else "L")
    out = {}
    for t, p in teams.items():
        rs_pg, ra_pg = p["rs"] / p["gp"], p["ra"] / p["gp"]
        pythag = rs_pg ** 1.83 / (rs_pg ** 1.83 + ra_pg ** 1.83) if (rs_pg + ra_pg) else 0.5
        out[t] = {
            "gp": p["gp"], "w": p["w"], "l": p["l"],
            "rs_pg": round(rs_pg, 2), "ra_pg": round(ra_pg, 2),
            "pythag": round(pythag, 3),
            "last10": "".join(p["res"][-10:]),
            "elo": elo.get(t), "elo_rank": rank.get(t),
        }
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    games: list = []
    for season in SEASONS:
        games.extend(fetch_season_games(season))
    if not games:
        raise SystemExit("no completed games fetched - check statsapi availability")
    as_of = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    latest = max(g["date"] for g in games)
    profiles = {
        "as_of": as_of, "data_through": latest,
        "window": f"{SEASONS[0]}-{SEASONS[-1]} regular+postseason finals",
        "elo_note": f"simple Elo k={ELO_K} hfa={ELO_HFA} over window; rank within MLB",
        "teams": build_profiles(games, SEASONS[-1]),
    }
    meta = {
        "as_of": as_of, "source": "statsapi.mlb.com schedule endpoint",
        "games_total": len(games), "data_through": latest,
        "teams_profiled": len(profiles["teams"]),
        "sia_note": "In-season staleness window 2 days; apply DATA_STALE penalty beyond it",
    }
    (OUT / "team_profiles.json").write_text(json.dumps(profiles, separators=(",", ":")), encoding="utf-8")
    (OUT / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(f"distilled {meta['teams_profiled']} teams from {len(games)} games; through {latest}")


if __name__ == "__main__":
    main()
