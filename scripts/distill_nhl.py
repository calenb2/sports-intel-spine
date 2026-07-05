"""Distill NHL results (api-web.nhle.com) into GPT-ready JSON.

v1 scope: results-based team profiles + simple Elo over last two seasons.
MoneyPuck xG enrichment is R4.2.

Outputs (distillates/nhl/): team_profiles.json, meta.json
"""
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "distillates" / "nhl"
TRICODES = [
    "ANA","BOS","BUF","CGY","CAR","CHI","COL","CBJ","DAL","DET","EDM","FLA",
    "LAK","MIN","MTL","NSH","NJD","NYI","NYR","OTT","PHI","PIT","SEA","SJS",
    "STL","TBL","TOR","UTA","VAN","VGK","WPG","WSH",
]
SEASONS = ["20242025", "20252026"]
ELO_K = 6.0
ELO_HFA = 33.0
ELO_START = 1500.0


def fetch_team_season(tricode: str, season: str) -> list:
    url = f"https://api-web.nhle.com/v1/club-schedule-season/{tricode}/{season}"
    try:
        with urllib.request.urlopen(url, timeout=45) as r:
            data = json.load(r)
    except Exception as e:
        print(f"warn: {tricode} {season}: {e}")
        return []
    games = []
    for g in data.get("games", []):
        if g.get("gameState") not in ("OFF", "FINAL"):
            continue
        ht, at = g.get("homeTeam", {}), g.get("awayTeam", {})
        if ht.get("score") is None or at.get("score") is None:
            continue
        games.append({
            "id": g.get("id"), "date": g.get("gameDate", ""), "season": season,
            "type": g.get("gameType", 2),  # 2=regular, 3=playoffs
            "home": ht.get("abbrev", ""), "away": at.get("abbrev", ""),
            "hs": int(ht["score"]), "as_": int(at["score"]),
            "last_period": (g.get("gameOutcome", {}) or {}).get("lastPeriodType", "REG"),
        })
    return games


def fetch_all() -> list:
    seen, games = set(), []
    for season in SEASONS:
        for tri in TRICODES:
            for g in fetch_team_season(tri, season):
                if g["id"] in seen:
                    continue
                seen.add(g["id"])
                if g["type"] in (2, 3):
                    games.append(g)
    return games


def run_elo(games: list) -> dict:
    elo: dict = {}
    for g in sorted(games, key=lambda x: x["date"]):
        h, a = g["home"], g["away"]
        eh, ea = elo.get(h, ELO_START), elo.get(a, ELO_START)
        exp_h = 1.0 / (1.0 + 10 ** (-((eh + ELO_HFA) - ea) / 400.0))
        res_h = 1.0 if g["hs"] > g["as_"] else 0.0
        # dampen OT/SO decisions
        k = ELO_K * (0.75 if g["last_period"] in ("OT", "SO") else 1.0)
        elo[h] = eh + k * (res_h - exp_h)
        elo[a] = ea + k * ((1 - res_h) - (1 - exp_h))
    return {t: round(v) for t, v in elo.items()}


def build_profiles(games: list, latest_season: str) -> dict:
    elo = run_elo(games)
    rank = {t: i + 1 for i, (t, _) in enumerate(sorted(elo.items(), key=lambda x: -x[1]))}
    cur = [g for g in games if g["season"] == latest_season]
    teams: dict = {}
    for g in sorted(cur, key=lambda x: x["date"]):
        for side, gf, ga in (("home", "hs", "as_"), ("away", "as_", "hs")):
            t = g[side]
            p = teams.setdefault(t, {"gp": 0, "w": 0, "l": 0, "otl": 0, "gf": 0, "ga": 0, "res": []})
            p["gp"] += 1
            p["gf"] += g[gf]
            p["ga"] += g[ga]
            won = g[gf] > g[ga]
            if won:
                p["w"] += 1
                p["res"].append("W")
            elif g["last_period"] in ("OT", "SO"):
                p["otl"] += 1
                p["res"].append("O")
            else:
                p["l"] += 1
                p["res"].append("L")
    out = {}
    for t, p in teams.items():
        out[t] = {
            "season": latest_season,
            "gp": p["gp"], "w": p["w"], "l": p["l"], "otl": p["otl"],
            "gf_pg": round(p["gf"] / p["gp"], 2), "ga_pg": round(p["ga"] / p["gp"], 2),
            "last10": "".join(p["res"][-10:]),
            "elo": elo.get(t), "elo_rank": rank.get(t),
        }
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    games = fetch_all()
    if len(games) < 500:
        raise SystemExit(f"suspiciously few NHL games fetched ({len(games)}) - check api-web availability")
    as_of = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    latest_season = SEASONS[-1]
    profiles = {
        "as_of": as_of,
        "data_through": max(g["date"] for g in games),
        "window_seasons": SEASONS,
        "elo_note": f"simple Elo k={ELO_K} hfa={ELO_HFA}, OT/SO dampened; records/last10 from {latest_season} (W-L-OTL)",
        "teams": build_profiles(games, latest_season),
    }
    meta = {
        "as_of": as_of, "source": "api-web.nhle.com club-schedule-season",
        "games_total": len(games), "data_through": profiles["data_through"],
        "teams_profiled": len(profiles["teams"]),
        "sia_note": "Offseason: staleness window 30d. In season: 2d, nightly cron. xG via MoneyPuck = R4.2",
    }
    (OUT / "team_profiles.json").write_text(json.dumps(profiles, separators=(",", ":")), encoding="utf-8")
    (OUT / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(f"distilled {meta['teams_profiled']} teams from {len(games)} games; through {meta['data_through']}")


if __name__ == "__main__":
    main()
