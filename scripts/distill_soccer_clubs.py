"""Distill club soccer results (football-data.co.uk CSVs) into GPT-ready JSON.

Leagues: EPL (E0), Championship (E1), La Liga (SP1), Serie A (I1),
Bundesliga (D1), Ligue 1 (F1). Seasons: last two completed + current when
published. Closing-odds columns are preserved to data/soccer_clubs/raw for the
market-calibration layer.

Outputs (distillates/soccer_clubs/): team_profiles.json, meta.json
"""
import csv
import io
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "distillates" / "soccer_clubs"
RAW = ROOT / "data" / "soccer_clubs" / "raw"
LEAGUES = {"E0": "EPL", "E1": "Championship", "SP1": "La Liga", "I1": "Serie A", "D1": "Bundesliga", "F1": "Ligue 1"}
SEASON_CODES = ["2425", "2526", "2627"]  # 2627 404s until Aug 2026 - tolerated
ELO_K = 20.0
ELO_HFA = 60.0
ELO_START = 1500.0


def fetch_csv(season: str, code: str) -> list:
    url = f"https://www.football-data.co.uk/mmz4281/{season}/{code}.csv"
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            text = r.read().decode("utf-8", errors="replace")
    except Exception:
        return []
    (RAW / season).mkdir(parents=True, exist_ok=True)
    (RAW / season / f"{code}.csv").write_text(text, encoding="utf-8")
    rows = []
    for g in csv.DictReader(io.StringIO(text)):
        if not g.get("HomeTeam") or g.get("FTHG", "") in ("", None):
            continue
        try:
            rows.append({
                "date": g.get("Date", ""), "season": season, "league": code,
                "home": g["HomeTeam"], "away": g["AwayTeam"],
                "hs": int(float(g["FTHG"])), "as_": int(float(g["FTAG"])),
            })
        except (ValueError, KeyError):
            continue
    return rows


def parse_date(d: str) -> str:
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(d, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return d


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    games = []
    for season in SEASON_CODES:
        for code in LEAGUES:
            games.extend(fetch_csv(season, code))
    if not games:
        raise SystemExit("no club soccer rows fetched")
    for g in games:
        g["date"] = parse_date(g["date"])

    # per-league Elo + latest-season records
    latest = max(g["season"] for g in games)
    profiles: dict = {}
    for code, name in LEAGUES.items():
        lg = [g for g in games if g["league"] == code]
        if not lg:
            continue
        elo: dict = {}
        for g in sorted(lg, key=lambda x: x["date"]):
            h, a = g["home"], g["away"]
            eh, ea = elo.get(h, ELO_START), elo.get(a, ELO_START)
            exp_h = 1.0 / (1.0 + 10 ** (-((eh + ELO_HFA) - ea) / 400.0))
            res_h = 1.0 if g["hs"] > g["as_"] else (0.5 if g["hs"] == g["as_"] else 0.0)
            elo[h] = eh + ELO_K * (res_h - exp_h)
            elo[a] = ea + ELO_K * ((1 - res_h) - (1 - exp_h))
        rank = {t: i + 1 for i, (t, _) in enumerate(sorted(elo.items(), key=lambda x: -x[1]))}
        cur = [g for g in lg if g["season"] == latest]
        teams: dict = {}
        for g in sorted(cur, key=lambda x: x["date"]):
            for side, gf, ga in (("home", "hs", "as_"), ("away", "as_", "hs")):
                t = g[side]
                p = teams.setdefault(t, {"gp": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "res": []})
                p["gp"] += 1
                p["gf"] += g[gf]
                p["ga"] += g[ga]
                r = "W" if g[gf] > g[ga] else ("D" if g[gf] == g[ga] else "L")
                p[{"W": "w", "D": "d", "L": "l"}[r]] += 1
                p["res"].append(r)
        for t, p in teams.items():
            profiles[t] = {
                "league": name, "season_code": latest,
                "gp": p["gp"], "w": p["w"], "d": p["d"], "l": p["l"],
                "gf_pg": round(p["gf"] / p["gp"], 2), "ga_pg": round(p["ga"] / p["gp"], 2),
                "last10": "".join(p["res"][-10:]),
                "elo": round(elo.get(t, ELO_START)), "elo_rank_league": rank.get(t),
            }

    as_of = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    payload = {
        "as_of": as_of, "data_through": max(g["date"] for g in games),
        "leagues": list(LEAGUES.values()), "season_codes_found": sorted({g["season"] for g in games}),
        "elo_note": f"per-league Elo k={ELO_K} hfa={ELO_HFA}; elo_rank is within league",
        "teams": profiles,
    }
    meta = {
        "as_of": as_of, "source": "football-data.co.uk season CSVs",
        "games_total": len(games), "data_through": payload["data_through"],
        "teams_profiled": len(profiles),
        "sia_note": "Odds columns preserved in data/soccer_clubs/raw for market-calibration layer. Offseason until mid-Aug: weekly cron adequate.",
    }
    (OUT / "team_profiles.json").write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    (OUT / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(f"distilled {len(profiles)} club teams from {len(games)} games; through {payload['data_through']}")


if __name__ == "__main__":
    main()
