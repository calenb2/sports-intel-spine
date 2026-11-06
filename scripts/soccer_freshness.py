"""Fail-closed freshness policy for men's senior international results.

Calendar gaps are allowed only with a live fixture check, previous-window coverage,
and a reviewed calendar. FIFA is a witness, not a replacement results dataset.
"""
import argparse
import csv
import json
import os
import sys
import unicodedata
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
FIFA_URL = "https://api.fifa.com/api/v3/calendar/matches"
RESULT_GRACE_DAYS = 2  # Allow two complete UTC calendar days after the match date.
ACTIVE_LAG_DAYS = 7
MAX_LOOKBACK_DAYS = 180
ALIASES = {
    "usa": "united states", "korea republic": "south korea",
    "korea dpr": "north korea", "ir iran": "iran", "cote d'ivoire": "ivory coast",
    "turkiye": "turkey", "china pr": "china", "chinese taipei": "taiwan",
    "congo dr": "dr congo", "cabo verde": "cape verde", "czechia": "czech republic",
    "curacao": "curacao", "timor-leste": "timor leste",
    "st kitts and nevis": "saint kitts and nevis", "st. lucia": "saint lucia",
    "st vincent and the grenadines": "saint vincent and the grenadines",
    "us virgin islands": "united states virgin islands", "brunei darussalam": "brunei",
    "hong kong, china": "hong kong", "kyrgyz republic": "kyrgyzstan",
}


def iso(value):
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError(f"Invalid ISO date: {value!r}")
    return date.fromisoformat(value)


def team_name(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Missing team name")
    value = "".join(c for c in unicodedata.normalize("NFKD", value.casefold())
                    if not unicodedata.combining(c)).strip()
    return ALIASES.get(value, value)


def match_key(day, home, away):
    # Neutral venues and source home/away designations can differ.
    return (day, *sorted((team_name(home), team_name(away))))


def fixture_present(fixture, matches):
    # Providers use either local dates or UTC dates. Accept only the two dates
    # explicitly supplied by FIFA, not an arbitrary +/- one-day fuzzy match.
    days = {fixture["date"], fixture.get("utc_date", fixture["date"])}
    return any(match_key(day, *fixture["teams"]) in matches for day in days)


def read_results(path, today):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"date", "home_team", "away_team", "home_score", "away_score"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("results.csv missing required columns")
        matches = []
        for row in reader:
            day = iso(row["date"])
            if day > today:
                raise ValueError("Future result date in results.csv")
            for field in ("home_score", "away_score"):
                if not row[field].isdigit():
                    raise ValueError("Missing/invalid completed-result score")
            key = match_key(day, row["home_team"], row["away_team"])
            # Historic sources can contain two matches between the same teams
            # on one date. Preserve row count; keys are only fixture witnesses.
            matches.append(key)
    if not matches:
        raise ValueError("Empty results.csv")
    return matches


def merged_result_rows(path, supplements_path, today):
    source_matches = read_results(path, today)
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    provenance = {"source_rows_total": len(rows),
                  "source_data_through": str(max(m[0] for m in source_matches))}
    supplements = json.loads(supplements_path.read_text(encoding="utf-8"))
    if supplements["schema_version"] != 1 or iso(supplements["reviewed_on"]) > today:
        raise ValueError("Invalid/unreviewed result supplements")
    by_key = {}
    for row, key in zip(rows, source_matches):
        by_key.setdefault(key, []).append(row)
    added = 0
    seen = set()
    for row in supplements["results"]:
        day = iso(row["date"])
        if day > today or not row["source"].startswith("https://"):
            raise ValueError("Supplement future-dated or missing provenance")
        for field in ("home_score", "away_score"):
            if not isinstance(row[field], str) or not row[field].isdigit():
                raise ValueError("Invalid supplement score")
        if any(not row[k] for k in ("tournament", "city", "country")) or row["neutral"] not in ("TRUE", "FALSE"):
            raise ValueError("Incomplete supplement")
        key = match_key(day, row["home_team"], row["away_team"])
        if key in seen:
            raise ValueError("Duplicate supplement")
        seen.add(key)
        expected = {team_name(row[side + "_team"]): int(row[side + "_score"])
                    for side in ("home", "away")}
        existing = by_key.get(key, [])
        if existing:
            actual = [{team_name(r[side + "_team"]): int(r[side + "_score"])
                       for side in ("home", "away")} for r in existing]
            if len(existing) != 1 or actual[0] != expected:
                raise ValueError(f"Upstream/supplement conflict for {key}; review official report")
        else:
            rows.append({k: v for k, v in row.items() if k != "source"})
            added += 1
    provenance["supplemental_rows"] = added
    return rows, provenance


def correct_fixtures(fixtures, calendar):
    corrections = {c["id"]: c for c in calendar.get("fixture_corrections", [])}
    result = []
    for fixture in fixtures:
        correction = corrections.get(fixture["id"])
        if correction:
            original = match_key(iso(correction["date"]), *correction["teams"])
            if not correction["reason"] or not correction["source"].startswith("https://"):
                raise ValueError("Fixture correction lacks provenance")
            if match_key(fixture["date"], *fixture["teams"]) == original:
                if correction["action"] == "exclude":
                    continue
                if correction["action"] != "reschedule" or fixture["status"] != 1:
                    raise ValueError("Fixture correction no longer agrees with feed")
                day = iso(correction["new_date"])
                fixture = {**fixture, "date": day, "utc_date": day,
                           "correction_source": correction["source"]}
            elif not (correction["action"] == "reschedule"
                      and match_key(fixture["date"], *fixture["teams"])
                      == match_key(iso(correction["new_date"]), *correction["teams"])):
                raise ValueError("Fixture correction fingerprint changed; review it")
        result.append(fixture)
    return result


def calendar_periods(calendar, today):
    if calendar["schema_version"] != 1:
        raise ValueError("Unsupported calendar schema")
    start, end = iso(calendar["valid_from"]), iso(calendar["valid_through"])
    if not start <= today <= end or iso(calendar["reviewed_on"]) > today:
        raise ValueError("Calendar unreviewed for this date; update its coverage")
    if not calendar["sources"]:
        raise ValueError("Calendar has no provenance")
    periods = []
    for item in calendar["periods"]:
        a, b = iso(item["start"]), iso(item["end"])
        if not item["name"] or a > b:
            raise ValueError("Invalid calendar period")
        periods.append((a, b, item["name"]))
    if not periods:
        raise ValueError("Empty calendar")
    return sorted(periods)


def get_json(url):
    with urlopen(url, timeout=45) as response:
        return json.load(response)


def fetch_fixtures(start, end, fetch=get_json):
    """Split date ranges until *all* pages fit; FIFA currently caps at 500.

    Do not rely on undocumented team filters (observed to be silently ignored).
    Saturation at one second or an absent pagination marker fails closed.
    """
    by_id, urls = {}, []

    def visit(a, b):
        if len(urls) >= 128:
            raise ValueError("FIFA request budget exceeded")
        url = FIFA_URL + "?" + urlencode({
            "from": a.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "to": b.strftime("%Y-%m-%dT%H:%M:%SZ"), "count": 500,
        })
        urls.append(url)
        payload = fetch(url)
        if (not isinstance(payload, dict) or not isinstance(payload.get("Results"), list)
                or "ContinuationToken" not in payload):
            raise ValueError("Malformed FIFA response / pagination unknown")
        rows = payload["Results"]
        if payload["ContinuationToken"] or len(rows) >= 500:
            if a == b:
                raise ValueError(f"FIFA instant {a} truncated; cannot prove coverage")
            if a.date() != b.date():
                middle_day = a.date() + (b.date() - a.date()) // 2
                mid = datetime.combine(middle_day, datetime.max.time().replace(microsecond=0),
                                       timezone.utc)
            else:
                mid = a + timedelta(seconds=int((b - a).total_seconds()) // 2)
            visit(a, mid)
            visit(mid + timedelta(seconds=1), b)
            return
        for row in rows:
            if not isinstance(row, dict) or not row.get("IdMatch"):
                raise ValueError("FIFA match missing ID")
            timestamp = datetime.fromisoformat(row["Date"].replace("Z", "+00:00"))
            if not a <= timestamp <= b:
                raise ValueError("FIFA ignored requested date bounds")
            old = by_id.get(row["IdMatch"])
            if old is not None and old != row:
                raise ValueError("Conflicting FIFA match IDs")
            by_id[row["IdMatch"]] = row

    visit(datetime.combine(start, datetime.min.time(), timezone.utc),
          datetime.combine(end, datetime.max.time().replace(microsecond=0), timezone.utc))
    return list(by_id.values()), urls


def senior_fixtures(rows):
    selected = []
    wanted = {"TeamType": 1, "AgeType": 7, "Gender": 1, "FootballType": 0}
    scopes = {}
    for row in rows:
        if not row.get("IdCompetition"):
            continue
        for team in (row.get("Home"), row.get("Away")):
            if isinstance(team, dict):
                outside = any(type(team.get(k)) is int and team[k] != v
                              for k, v in wanted.items())
                scopes.setdefault(row["IdCompetition"], set()).add(
                    False if outside else True if all(team.get(k) == v
                                                     for k, v in wanted.items()) else None)
    for row in rows:
        teams = [row.get("Home"), row.get("Away")]
        if scopes.get(row.get("IdCompetition")) == {False}:
            continue
        # The all-sports feed contains unnamed bracket placeholders. These are
        # not identifiable match witnesses; count/report them separately.
        if teams == [None, None] and row.get("MatchStatus") == 1:
            continue
        # One definitely out-of-scope participant excludes this match even if
        # the other participant has not yet been assigned to a bracket slot.
        if any(isinstance(t, dict) and any(type(t.get(k)) is int and t[k] != v
                                          for k, v in wanted.items()) for t in teams):
            continue
        if any(not isinstance(t, dict) for t in teams):
            raise ValueError("FIFA fixture has unknown team classification")
        flags = []
        for team in teams:
            values = [team[k] for k in ("TeamType", "AgeType", "Gender", "FootballType")]
            if any(type(v) is not int for v in values):
                raise ValueError("FIFA team classification missing/invalid")
            flags.append(values == [1, 7, 1, 0])
        if not all(flags):
            continue
        day = iso((row.get("LocalDate") or row["Date"])[:10])
        names = []
        for team in teams:
            labels = team["TeamName"]
            label = next((v["Description"] for v in labels
                          if v["Locale"].lower().startswith("en")), None)
            names.append(team_name(label))
        status = row["MatchStatus"]
        if type(status) is not int:
            raise ValueError("Unknown FIFA match status")
        # 0 is completed, 1 is scheduled (observed live). All other statuses
        # require review if overdue and absent; never assume they mean cancelled.
        selected.append({"date": day, "teams": names, "status": status,
                         "utc_date": iso(row["Date"][:10]), "id": row["IdMatch"]})
    return selected


def evaluate(matches, meta, previous, calendar, fixtures, today):
    periods = calendar_periods(calendar, today)
    latest = max(m[0] for m in matches)
    if (iso(meta["data_through"]) != latest or meta["rows_total"] != len(matches)
            or iso(meta["as_of"]) != today or meta["teams_profiled"] < 200):
        raise ValueError("Distillate metadata inconsistent/incomplete")
    if latest < iso(previous["data_through"]) or len(matches) < previous["rows_total"]:
        raise ValueError("Upstream regressed vs last published data")
    if (meta.get("source_rows_total", meta["rows_total"])
            < previous.get("source_rows_total", previous["rows_total"])
            or iso(meta.get("source_data_through", meta["data_through"]))
            < iso(previous.get("source_data_through", previous["data_through"]))):
        raise ValueError("Primary source regressed; supplements cannot conceal it")
    matches = set(matches)
    if (today - latest).days > MAX_LOOKBACK_DAYS:
        raise ValueError("Results exceed maximum verifiable lookback")
    completed = [p for p in periods if p[1] < today]
    active = [p for p in periods if p[0] <= today <= p[1]]
    future = [p for p in periods if p[0] > today]
    floor = max((p[1] - timedelta(days=RESULT_GRACE_DAYS) for p in completed),
                default=iso(calendar["valid_from"]) - timedelta(days=ACTIVE_LAG_DAYS))
    for start, _, _ in active:
        if today > start + timedelta(days=ACTIVE_LAG_DAYS):
            floor = max(floor, today - timedelta(days=ACTIVE_LAG_DAYS))
    errors = []
    if latest < floor:
        errors.append(f"Source stalled: latest {latest}, expected at least {floor}")
    # A feed with no overlapping known match cannot establish an idle period.
    overlap = any(fixture_present(f, matches)
                  and f["status"] == 0 for f in fixtures)
    if not overlap:
        errors.append("FIFA feed has no completed overlap with source; coverage unverified")
    pending, missing = [], []
    witnesses = fixtures + [{"date": iso(r["date"]), "teams": r["teams"],
                             "status": 0, "id": r["source"]}
                            for r in calendar.get("known_results", [])]
    witnesses = {match_key(f["date"], *f["teams"]): f for f in witnesses}
    for fixture in witnesses.values():
        day = fixture["date"]
        if day > today or fixture_present(fixture, matches):
            continue
        detail = {**fixture, "date": day.isoformat(),
                  "deadline": (day + timedelta(days=RESULT_GRACE_DAYS + 1)).isoformat()}
        if (today - day).days > RESULT_GRACE_DAYS:
            missing.append(detail)
        else:
            pending.append(detail)
    if missing:
        errors.append(f"{len(missing)} overdue fixture witnesses absent from results")
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(), "as_of": today.isoformat(),
        "data_through": latest.isoformat(), "age_days": (today - latest).days,
        "state": "blocked" if errors else ("awaiting_results" if pending else
                  "active" if active else "between_windows"),
        "publish_allowed": not errors, "errors": errors,
        "active_periods": [p[2] for p in active],
        "next_period_start": min((p[0] for p in future), default=None),
        "calendar_valid_through": calendar["valid_through"],
        "required_data_through": floor.isoformat(),
        "missing_fixtures": missing, "pending_fixtures": pending,
        "fixture_count": len(fixtures),
        "source_data_through": meta.get("source_data_through", meta["data_through"]),
        "supplemental_rows": meta.get("supplemental_rows", 0),
        "limitations": "FIFA coverage is not exhaustive; see docs/SOCCER_FRESHNESS.md",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--previous-meta", type=Path, required=True)
    parser.add_argument("--results", type=Path, default=ROOT / "data/soccer/raw/results.csv")
    parser.add_argument("--meta", type=Path, default=ROOT / "distillates/soccer/meta.json")
    parser.add_argument("--calendar", type=Path, default=ROOT / "data/soccer/calendar.json")
    parser.add_argument("--supplements", type=Path, default=ROOT / "data/soccer/result_supplements.json")
    parser.add_argument("--output", type=Path, default=ROOT / "distillates/soccer/freshness_status.json")
    args = parser.parse_args(argv)
    today = datetime.now(timezone.utc).date()
    urls = []
    try:
        calendar = json.loads(args.calendar.read_text(encoding="utf-8"))
        calendar_periods(calendar, today)
        merged, provenance = merged_result_rows(args.results, args.supplements, today)
        matches = [match_key(iso(r["date"]), r["home_team"], r["away_team"]) for r in merged]
        meta = json.loads(args.meta.read_text(encoding="utf-8"))
        if any(meta.get(k) != v for k, v in provenance.items()):
            raise ValueError("Distillate source/supplement provenance mismatch")
        # Supplements must not shorten the independent audit of a stalled source.
        latest = iso(provenance["source_data_through"])
        if (today - latest).days > MAX_LOOKBACK_DAYS:
            raise ValueError("Results exceed maximum verifiable lookback")
        rows, urls = fetch_fixtures(latest - timedelta(days=7), today)
        result = evaluate(matches, meta,
                          json.loads(args.previous_meta.read_text(encoding="utf-8")),
                          calendar, correct_fixtures(senior_fixtures(rows), calendar), today)
        result["unidentified_scheduled_placeholders"] = sum(
            row.get("Home") is None and row.get("Away") is None
            and row.get("MatchStatus") == 1 for row in rows)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        result = {"as_of": today.isoformat(), "state": "blocked", "publish_allowed": False,
                  "errors": [f"Freshness verification failed: {exc}"]}
    result["fixture_source"] = FIFA_URL
    result["fixture_queries"] = urls
    text = json.dumps(result, indent=2, default=str) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as handle:
            handle.write("## Soccer freshness\n```json\n" + text + "```\n")
    return 0 if result["publish_allowed"] else 1


if __name__ == "__main__":
    sys.exit(main())
