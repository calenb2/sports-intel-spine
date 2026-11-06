import importlib.util
import io
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import mlb_season as policy
import distill_mlb as distill


def game(day, kind="R", state="F"):
    return {"officialDate": day, "gameType": kind,
            "status": {"codedGameState": state},
            "teams": {"home": {"score": 4}, "away": {"score": 2}}}


def year(y, games=()):
    return {"year": y, "season": {"regularSeasonStartDate": f"{y}-03-25",
            "seasonEndDate": f"{y}-10-31", "springStartDate": f"{y}-02-19"},
            "games": list(games), "sources": [f"https://statsapi.mlb.com/{y}"]}


def fixture(today, latest, games=None):
    y = today.year
    years = {y-1: year(y-1, [game(f"{y-1}-10-28", "W")]),
             y: year(y, games if games is not None else [game(latest)]),
             y+1: year(y+1, [game(f"{y+1}-02-19", "S", "S"), game(f"{y+1}-03-25", "R", "S")])}
    meta = {"as_of": today.isoformat(), "data_through": latest, "teams_profiled": 30}
    return meta, years


class PolicyTests(unittest.TestCase):
    def test_in_season_current(self):
        today = date(2026, 7, 1)
        self.assertEqual(policy.evaluate(today, *fixture(today, "2026-06-30"))["phase"], "active")

    def test_stale_in_season_fails(self):
        today = date(2026, 7, 1)
        with self.assertRaisesRegex(ValueError, "STALE"):
            policy.evaluate(today, *fixture(today, "2026-06-20"))

    def test_missing_postseason_finals_fails_even_offseason(self):
        today = date(2026, 11, 1)
        meta, years = fixture(today, "2026-10-28", [game("2026-10-28", "W")])
        meta["data_through"] = "2026-09-27"
        with self.assertRaisesRegex(ValueError, "DATA_MISMATCH"):
            policy.evaluate(today, meta, years)

    def test_offseason_older_results_valid_and_restart_logged(self):
        today = date(2026, 12, 15)
        result = policy.evaluate(today, *fixture(today, "2026-10-28", [game("2026-10-28", "W")]))
        self.assertEqual(result["phase"], "offseason")
        self.assertEqual(result["automatic_regular_season_check_utc"], "2027-03-25T09:00:00Z")
        self.assertEqual(result["next_spring_training_date"], "2027-02-19")
        self.assertFalse(result["spring_training_in_ratings"])

    def test_year_rollover_retains_previous_finals(self):
        today = date(2027, 1, 1)
        result = policy.evaluate(today, *fixture(today, "2026-10-28", []))
        self.assertEqual(result["profile_season"], 2026)
        self.assertEqual(result["next_season"], 2027)
        self.assertEqual(result["phase"], "offseason")

    def test_spring_training_not_ratings_restart(self):
        today = date(2027, 2, 25)
        result = policy.evaluate(today, *fixture(today, "2026-10-28", [game("2027-02-24", "S")]))
        self.assertEqual(result["phase"], "spring_training")
        self.assertEqual(result["next_regular_season_date"], "2027-03-25")

    def test_opening_day_grace(self):
        today = date(2027, 3, 25)
        result = policy.evaluate(today, *fixture(today, "2026-10-28", [game("2027-03-25", state="S")]))
        self.assertEqual(result["freshness"], "opening_grace")
        self.assertEqual(result["phase"], "active")

    def test_empty_current_year_cannot_masquerade_as_offseason(self):
        today = date(2027, 11, 1)
        with self.assertRaisesRegex(ValueError, "no scored finals"):
            policy.evaluate(today, *fixture(today, "2026-10-28", []))

    def test_postseason_extension_overrides_calendar(self):
        today = date(2026, 11, 2)
        result = policy.evaluate(today, *fixture(today, "2026-10-31", [game("2026-10-31", "W"), game("2026-11-02", "W", "S")]))
        self.assertEqual(result["phase"], "active")

    def test_postseason_stale_extension_fails(self):
        today = date(2026, 11, 8)
        with self.assertRaisesRegex(ValueError, "STALE"):
            policy.evaluate(today, *fixture(today, "2026-10-31", [game("2026-10-31", "W"), game("2026-11-08", "W", "S")]))

    def test_early_world_series_clinch_enters_offseason(self):
        today = date(2026, 10, 30)
        games = [game(f"2026-10-{d}", "W") for d in (20, 21, 23, 24)]
        for g in games:
            g["teams"]["home"]["team"] = {"id": 1}
        result = policy.evaluate(today, *fixture(today, "2026-10-24", games))
        self.assertEqual(result["phase"], "offseason")
        self.assertTrue(result["world_series_clinch_verified"])

    def test_schedule_opener_overrides_metadata_consistently(self):
        today = date(2027, 3, 18)
        result = policy.evaluate(today, *fixture(today, "2026-10-28", [game("2027-03-18", state="S")]))
        self.assertEqual(result["phase"], "active")
        self.assertEqual(result["current_regular_season_start"], "2027-03-18")

    def test_early_clinch_does_not_hide_outstanding_game(self):
        today = date(2026, 10, 30)
        games = [game(f"2026-10-{d}", "W") for d in (20, 21, 23, 24)]
        for g in games:
            g["teams"]["home"]["team"] = {"id": 1}
        games.append(game("2026-10-30", "W", "S"))
        with self.assertRaisesRegex(ValueError, "STALE"):
            policy.evaluate(today, *fixture(today, "2026-10-24", games))

    def test_future_dates_unpublished_explicitly_unknown(self):
        today = date(2026, 11, 1)
        meta, years = fixture(today, "2026-10-28")
        years[2027] = {"season": None, "games": [], "sources": []}
        result = policy.evaluate(today, meta, years)
        self.assertIsNone(result["automatic_regular_season_check_utc"])
        self.assertEqual(result["next_regular_season_date_basis"], "not published")

    def test_api_failure_does_not_become_offseason(self):
        with patch.object(policy, "get_json", side_effect=OSError("API unavailable")):
            with self.assertRaises(OSError):
                policy.load_year(2027, required=False)

    def test_malformed_response_rejected(self):
        with patch.object(policy, "get_json", return_value={}):
            with self.assertRaisesRegex(ValueError, "malformed"):
                policy.load_year(2027, required=False)

    def test_empty_required_schedule_rejected(self):
        season = dict(year(2026)["season"], seasonId="2026")
        with patch.object(policy, "get_json", side_effect=[{"seasons": [season]}, {"dates": []}]):
            with self.assertRaisesRegex(ValueError, "empty required"):
                policy.load_year(2026)

    def test_stale_fetch_timestamp_rejected(self):
        today = date(2026, 11, 1)
        meta, years = fixture(today, "2026-10-28")
        meta["as_of"] = "2026-10-31"
        with self.assertRaisesRegex(ValueError, "not fetched today"):
            policy.evaluate(today, meta, years)

    def test_rollover_distiller_keeps_two_completed_seasons(self):
        class Clock:
            @staticmethod
            def now(tz):
                from datetime import datetime
                return datetime(2027, 1, 1, tzinfo=tz)
        calls = []
        def fetch(season):
            calls.append(season)
            return [] if season == 2027 else [{"date": f"{season}-10-28", "home": "Home", "away": "Away", "hs": 4, "as_": 2, "type": "W"}]
        with tempfile.TemporaryDirectory() as tmp, patch.object(distill, "OUT", Path(tmp)), patch.object(distill, "datetime", Clock), patch.object(distill, "fetch_season_games", side_effect=fetch):
            distill.main()
            meta = json.loads((Path(tmp) / "meta.json").read_text())
            self.assertEqual(meta["profile_season"], 2026)
            self.assertEqual(meta["teams_profiled"], 2)
            self.assertEqual(meta["games_total"], 2)
            self.assertEqual(calls, [2027, 2025, 2026])


if __name__ == "__main__":
    unittest.main()
