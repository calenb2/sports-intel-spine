import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

spec = importlib.util.spec_from_file_location(
    "distill_mlb", Path(__file__).resolve().parents[1] / "scripts/distill_mlb.py"
)
mlb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mlb)


def game(kind, status="F", home_score=4):
    return {"gameType": kind, "status": {"codedGameState": status},
            "teams": {"home": {"team": {"name": "Home"}, "score": home_score},
                      "away": {"team": {"name": "Away"}, "score": 2}}}


class MLBTests(unittest.TestCase):
    def test_schedule_requests_regular_and_every_postseason_round(self):
        # Model the API's exact game-type filter, not an unfiltered mock response.
        def schedule(url, timeout):
            query = parse_qs(urlparse(url).query)
            self.assertEqual(query["startDate"], ["2026-01-01"])
            self.assertEqual(query["endDate"], ["2026-12-31"])
            requested = set(query["gameTypes"][0].split(","))
            available = [game(t) for t in ("R", "F", "D", "L", "W", "S", "A")]
            payload = {"dates": [{"date": "2026-10-28", "games": [
                g for g in available if g["gameType"] in requested]}]}
            return io.BytesIO(json.dumps(payload).encode())
        with patch.object(mlb.urllib.request, "urlopen", side_effect=schedule):
            games = mlb.fetch_season_games(2026)
        self.assertEqual([g["type"] for g in games], ["R", "F", "D", "L", "W"])

    def test_only_scored_finals_are_included(self):
        payload = {"dates": [{"date": "2026-10-28", "games": [
            game("W"), game("W", "S"), game("W", "I"),
            game("W", home_score=None)]}]}
        with patch.object(mlb.urllib.request, "urlopen", return_value=io.BytesIO(json.dumps(payload).encode())):
            games = mlb.fetch_season_games(2026)
        self.assertEqual(len(games), 1)
        self.assertEqual(games[0]["type"], "W")

    def test_postseason_results_contribute_to_profiles(self):
        games = [{"date": "2026-10-28", "home": "Home", "away": "Away",
                  "hs": 4, "as_": 2, "type": "W"}]
        profiles = mlb.build_profiles(games, 2026)
        self.assertEqual(profiles["Home"]["gp"], 1)
        self.assertEqual(profiles["Home"]["w"], 1)
        self.assertEqual(profiles["Away"]["l"], 1)


if __name__ == "__main__":
    unittest.main()
