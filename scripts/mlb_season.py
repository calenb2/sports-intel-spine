"""Fail-closed MLB freshness policy and dated restart ledger (stdlib only).

The daily workflow stays enabled. Spring training is monitored but excluded from
regular/postseason ratings. Dates are refreshed from MLB, never hard-coded.
"""
import json
import os
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "distillates" / "mlb"
BASE = "https://statsapi.mlb.com/api/v1"
TYPES = {"R", "F", "D", "L", "W"}
MAX_LAG = 3


def get_json(url):
    with urllib.request.urlopen(url, timeout=60) as response:
        value = json.load(response)
    if not isinstance(value, dict):
        raise ValueError(f"invalid MLB response: {url}")
    return value


def load_year(year, required=True):
    season_url = f"{BASE}/seasons/{year}?sportId=1"
    schedule_url = f"{BASE}/schedule?sportId=1&season={year}&gameTypes=R,F,D,L,W,S"
    season_data, schedule = get_json(season_url), get_json(schedule_url)
    if not isinstance(season_data.get("seasons"), list) or not isinstance(schedule.get("dates"), list):
        raise ValueError(f"malformed season/schedule response for {year}")
    seasons = [s for s in season_data["seasons"] if str(s.get("seasonId")) == str(year)]
    if required and len(seasons) != 1:
        raise ValueError(f"required season metadata unavailable for {year}")
    season = seasons[0] if seasons else None
    if season:
        for key in ("regularSeasonStartDate", "seasonEndDate"):
            date.fromisoformat(season[key])
        if season["regularSeasonStartDate"] > season["seasonEndDate"]:
            raise ValueError("reversed season dates")
    games = []
    for day in schedule["dates"]:
        for game in day["games"]:
            # Keep provider's officialDate, not UTC gameDate (may be next day).
            date.fromisoformat(game["officialDate"])
            if game["gameType"] not in TYPES | {"S"} or "codedGameState" not in game["status"]:
                raise ValueError("invalid game type/status")
            games.append(game)
    if required and not any(g["gameType"] in TYPES for g in games):
        raise ValueError(f"empty required regular/postseason schedule for {year}")
    return {"year": year, "season": season, "games": games,
            "sources": [season_url, schedule_url]}


def scored_final(game):
    return (game["gameType"] in TYPES and game["status"]["codedGameState"] == "F"
            and all(game.get("teams", {}).get(side, {}).get("score") is not None
                    for side in ("home", "away")))


def world_series_complete(games):
    """A best-of-seven clinch is evidence; a quiet schedule alone is not."""
    wins = {}
    for game in games:
        if game["gameType"] != "W" or not scored_final(game):
            continue
        home, away = game["teams"]["home"], game["teams"]["away"]
        if home["score"] == away["score"]:
            continue
        winner = home if home["score"] > away["score"] else away
        identity = winner.get("team", {}).get("id")
        if identity is None:
            continue
        wins[identity] = wins.get(identity, 0) + 1
    return max(wins.values(), default=0) >= 4


def evaluate(today, meta, years):
    """Pure policy. Network exceptions cannot become a valid offseason status."""
    current, previous = years[today.year], years[today.year - 1]
    current_meta = current["season"]
    if not current_meta or not previous["season"]:
        raise ValueError("missing required season metadata")
    all_games = previous["games"] + current["games"]
    finals = [g for g in all_games if scored_final(g) and g["officialDate"] <= today.isoformat()]
    if not finals:
        raise ValueError("no scored finals in authoritative schedules")
    latest = max(g["officialDate"] for g in finals)
    if meta["data_through"] != latest:
        raise ValueError(f"DATA_MISMATCH: distillate={meta['data_through']}, MLB finals={latest}")
    if meta["as_of"] != today.isoformat():
        raise ValueError("distillate was not fetched today (UTC)")
    if meta["teams_profiled"] <= 0:
        raise ValueError("empty team profiles")

    regular_dates = sorted(g["officialDate"] for g in current["games"] if g["gameType"] == "R")
    start = date.fromisoformat(regular_dates[0] if regular_dates else current_meta["regularSeasonStartDate"])
    end = date.fromisoformat(current_meta["seasonEndDate"])
    if today > start + timedelta(days=MAX_LAG) and not any(
            scored_final(g) for g in current["games"]):
        raise ValueError("current season has no scored finals; not safe to infer offseason")
    active = start <= today <= end
    # Schedule evidence overrides nominal calendar bounds for extended playoffs.
    outstanding = [g for g in all_games if g["gameType"] in TYPES
                   and g["officialDate"] >= latest
                   and g["status"]["codedGameState"] not in {"F", "C", "D"}]
    if outstanding and today >= start:
        active = True
    complete = world_series_complete([g for g in current["games"] if g["officialDate"] <= today.isoformat()])
    if complete and not outstanding:
        active = False
    age = (today - date.fromisoformat(latest)).days
    # Opening day: prior-season results are expected until finals arrive.
    opening_grace = start <= today <= start + timedelta(days=MAX_LAG)
    if active and age > MAX_LAG and not opening_grace:
        raise ValueError(f"STALE: active-season results lag {age} days (limit {MAX_LAG})")

    next_year = today.year if today < start else today.year + 1
    nxt = years.get(next_year, {"season": None, "games": [], "sources": []})
    next_meta = nxt["season"] or {}
    regular = sorted(g["officialDate"] for g in nxt["games"] if g["gameType"] == "R")
    spring = sorted(g["officialDate"] for g in nxt["games"] if g["gameType"] == "S")
    # Prefer actual schedule; a valid-but-empty future schedule is explicitly unknown.
    resume = regular[0] if regular else next_meta.get("regularSeasonStartDate")
    spring_start = spring[0] if spring else next_meta.get("springStartDate")
    spring_now = current_meta.get("springStartDate")
    phase = "active" if active else ("spring_training" if spring_now and spring_now <= today.isoformat() < start.isoformat() else "offseason")
    return {
        "checked_on_utc": today.isoformat(), "phase": phase,
        "data_through": latest, "data_age_days": age,
        "freshness": "opening_grace" if active and age > MAX_LAG else ("current" if active else "last_completed_season_retained"),
        "active_season_max_lag_days": MAX_LAG,
        "profile_season": meta.get("profile_season", int(latest[:4])),
        "current_regular_season_start": start.isoformat(),
        "world_series_clinch_verified": complete,
        "next_season": next_year,
        "next_spring_training_date": spring_start,
        "next_regular_season_date": resume,
        "next_regular_season_date_basis": "MLB schedule" if regular else ("MLB season metadata" if resume else "not published"),
        "next_spring_training_date_basis": "MLB schedule" if spring else ("MLB season metadata" if spring_start else "not published"),
        "automatic_regular_season_check_utc": f"{resume}T09:00:00Z" if resume else None,
        "next_schedule_check_utc": f"{(today + timedelta(days=1)).isoformat()}T09:00:00Z",
        "schedule_policy": "Daily 09:00 UTC recheck remains enabled; restart dates are officialDate calendar dates, not first-pitch times. GitHub cron may run late.",
        "spring_training_in_ratings": False,
        "sources": sorted({url for y in years.values() for url in y["sources"]}),
    }


def main():
    today = datetime.now(timezone.utc).date()
    try:
        # The current season can legitimately have no games before publication.
        # Required previous season supplies final-result evidence at year rollover.
        years = {today.year - 1: load_year(today.year - 1),
                 today.year: load_year(today.year, required=False),
                 today.year + 1: load_year(today.year + 1, required=False)}
        if not years[today.year]["season"]:
            raise ValueError("current season metadata unavailable; cannot classify offseason safely")
        status = evaluate(today, json.loads((OUT / "meta.json").read_text()), years)
        status["checked_at_utc"] = datetime.now(timezone.utc).isoformat()
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "season_status.json").write_text(json.dumps(status, indent=2) + "\n")
        print(json.dumps(status, indent=2))
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as summary:
                summary.write("## MLB season / restart ledger\n\n```json\n" + json.dumps(status, indent=2) + "\n```\n")
    except Exception as exc:
        print(f"MLB season check FAILED (no publication): {exc}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
