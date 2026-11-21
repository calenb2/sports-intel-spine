import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import soccer_freshness as s
import soccer_transport as transport
import pull_soccer as pull
from http.client import IncompleteRead
from urllib.error import HTTPError


class FakeResponse:
    """Minimal stand-in for an http.client response used by the transport."""

    def __init__(self, body, status=200, headers=None):
        self.body, self.status = body, status
        self.headers = headers or {}

    def read(self, n=-1):
        if n is None or n < 0:
            data, self.body = self.body, b""
            return data
        data, self.body = self.body[:n], self.body[n:]
        return data

    def getcode(self):
        return self.status

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def fixture(day="2026-10-06", home="USA", away="Canada", status=0):
    return {"date": date.fromisoformat(day), "teams": [home, away],
            "status": status, "id": "test"}


def api_row(day="2026-10-06T12:00:00Z"):
    def team(name):
        return {"TeamType": 1, "AgeType": 7, "Gender": 1, "FootballType": 0,
                "TeamName": [{"Locale": "en-GB", "Description": name}]}
    return {"IdMatch": "1", "Date": day, "LocalDate": day,
            "Home": team("USA"), "Away": team("Canada"), "MatchStatus": 0}


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.calendar = {
            "schema_version": 1, "reviewed_on": "2026-10-01",
            "valid_from": "2026-09-21", "valid_through": "2026-12-31",
            "sources": ["https://inside.fifa.com"],
            "periods": [
                {"start": "2026-09-21", "end": "2026-10-06", "name": "October"},
                {"start": "2026-11-09", "end": "2026-11-17", "name": "November"},
            ], "known_results": [],
        }
        self.matches = {s.match_key(date(2026, 10, 6), "United States", "Canada")}
        self.fixtures = [fixture()]

    def evaluate(self, day="2026-11-06", latest=None, previous=None):
        if latest:
            self.matches.add(s.match_key(date.fromisoformat(latest), "England", "Spain"))
        meta = {"data_through": str(max(m[0] for m in self.matches)),
                "rows_total": len(self.matches), "teams_profiled": 257, "as_of": day}
        return s.evaluate(self.matches, meta, previous or meta, self.calendar,
                          self.fixtures, date.fromisoformat(day))

    def test_31_day_gap_allowed_with_live_overlap(self):
        result = self.evaluate()
        self.assertTrue(result["publish_allowed"])
        self.assertEqual(result["state"], "between_windows")
        self.assertEqual(result["age_days"], 31)

    def test_no_feed_is_not_proof_of_no_matches(self):
        self.fixtures = []
        self.assertFalse(self.evaluate()["publish_allowed"])

    def test_new_window_opening_grace_then_stall(self):
        self.assertTrue(self.evaluate("2026-11-09")["publish_allowed"])
        self.assertTrue(self.evaluate("2026-11-16")["publish_allowed"])
        self.assertFalse(self.evaluate("2026-11-17")["publish_allowed"])

    def test_active_results_resume(self):
        self.assertTrue(self.evaluate("2026-11-17", latest="2026-11-15")["publish_allowed"])

    def test_missing_completed_window_not_excused_by_next_break(self):
        self.assertFalse(self.evaluate("2026-11-19")["publish_allowed"])
        self.assertTrue(self.evaluate("2026-11-19", latest="2026-11-17")["publish_allowed"])

    def test_overlapping_tournament_starts_monitoring_earlier(self):
        self.calendar["periods"].append(
            {"start": "2026-11-04", "end": "2026-11-17", "name": "SAFF"})
        result = self.evaluate("2026-11-12")
        self.assertFalse(result["publish_allowed"])
        self.assertEqual(len(result["active_periods"]), 2)

    def test_off_window_result_pending_then_overdue(self):
        self.fixtures.append(fixture("2026-11-05", "India", "Pakistan"))
        self.assertEqual(self.evaluate()["state"], "awaiting_results")
        self.assertTrue(self.evaluate("2026-11-07")["publish_allowed"])
        self.assertFalse(self.evaluate("2026-11-08")["publish_allowed"])

    def test_scheduled_or_unknown_overdue_fixture_fails_closed(self):
        for status in (1, 7, 99):
            with self.subTest(status=status):
                self.fixtures = [fixture(), fixture("2026-11-02", "India", "Pakistan", status)]
                self.assertFalse(self.evaluate()["publish_allowed"])

    def test_known_result_detected_when_feed_omits_it(self):
        self.calendar["known_results"] = [
            {"date": "2026-11-02", "teams": ["India", "Pakistan"], "source": "AIFF"}]
        self.assertFalse(self.evaluate()["publish_allowed"])

    def test_recent_other_result_does_not_mask_missing_fixture(self):
        self.fixtures.append(fixture("2026-11-02", "India", "Pakistan"))
        self.assertFalse(self.evaluate(latest="2026-11-06")["publish_allowed"])

    def test_reversed_designation_and_alias_match(self):
        self.fixtures = [fixture(home="Canada", away="USA")]
        self.assertTrue(self.evaluate()["publish_allowed"])

    def test_utc_or_local_date_only(self):
        f = fixture("2026-10-05")
        f["utc_date"] = date(2026, 10, 6)
        self.assertTrue(s.fixture_present(f, self.matches))
        f["utc_date"] = date(2026, 10, 5)
        self.assertFalse(s.fixture_present(f, self.matches))

    def test_future_fixture_not_missing(self):
        self.fixtures.append(fixture("2026-11-09", "India", "Pakistan", 1))
        self.assertEqual(self.evaluate()["pending_fixtures"], [])

    def test_expired_or_future_review_calendar_rejected(self):
        for day in ("2027-01-01", "2026-09-30"):
            with self.subTest(day=day), self.assertRaises(ValueError):
                self.evaluate(day)

    def test_bad_calendar(self):
        for change in ({"schema_version": 2}, {"periods": []}, {"sources": []}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                s.calendar_periods({**self.calendar, **change}, date(2026, 11, 6))
        self.calendar["periods"][0]["end"] = "2026-09-20"
        with self.assertRaises(ValueError):
            self.evaluate()

    def test_regression_in_count_or_latest_rejected(self):
        for previous in ({"rows_total": 2, "data_through": "2026-10-06"},
                         {"rows_total": 1, "data_through": "2026-10-07"}):
            with self.subTest(previous=previous), self.assertRaises(ValueError):
                self.evaluate(previous=previous)

    def test_metadata_must_match_validated_source(self):
        base = {"rows_total": 1, "data_through": "2026-10-06",
                "as_of": "2026-11-06", "teams_profiled": 257}
        for change in ({"rows_total": 2}, {"data_through": "2026-11-07"},
                       {"as_of": "2026-11-05"}, {"teams_profiled": 0}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                s.evaluate(self.matches, {**base, **change}, base, self.calendar,
                           self.fixtures, date(2026, 11, 6))


class FeedTests(unittest.TestCase):
    def test_normal_response_and_local_date(self):
        row = api_row("2026-10-07T01:00:00Z")
        row["LocalDate"] = "2026-10-06T20:00:00Z"
        rows, urls = s.fetch_fixtures(date(2026, 10, 7), date(2026, 10, 7),
                                     lambda _: {"Results": [row], "ContinuationToken": None})
        self.assertEqual(s.senior_fixtures(rows)[0]["date"], date(2026, 10, 6))
        self.assertEqual(len(urls), 1)

    def test_pagination_splits_busy_day_without_truncation(self):
        row = api_row()
        def fetch(url):
            query = parse_qs(urlparse(url).query)
            a, b = query["from"][0], query["to"][0]
            if a.endswith("00:00:00Z") and b.endswith("23:59:59Z"):
                return {"Results": [], "ContinuationToken": "more"}
            return {"Results": [row] if a <= row["Date"] <= b else [],
                    "ContinuationToken": None}
        rows, urls = s.fetch_fixtures(date(2026, 10, 6), date(2026, 10, 6), fetch)
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(urls), 3)

    def test_saturation_never_silently_succeeds(self):
        with self.assertRaisesRegex(ValueError, "truncated"):
            s.fetch_fixtures(date(2026, 10, 6), date(2026, 10, 6),
                             lambda _: {"Results": [], "ContinuationToken": "more"})

    def test_malformed_feed_and_ignored_date_filters(self):
        for payload in ({}, {"Results": []}, {"Results": None, "ContinuationToken": None},
                        {"Results": [api_row("2026-09-01T00:00:00Z")], "ContinuationToken": None}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                s.fetch_fixtures(date(2026, 10, 6), date(2026, 10, 6), lambda _: payload)

    def test_http_failure_propagates(self):
        with self.assertRaises(OSError):
            s.fetch_fixtures(date(2026, 10, 6), date(2026, 10, 6),
                             lambda _: (_ for _ in ()).throw(OSError("offline")))

    def test_exclude_clubs_women_youth_futsal(self):
        for key, value in (("TeamType", 0), ("Gender", 2), ("AgeType", 5), ("FootballType", 1)):
            row = api_row()
            row["Home"][key] = value
            with self.subTest(key=key):
                self.assertEqual(s.senior_fixtures([row]), [])

    def test_unknown_classification_fails(self):
        row = api_row()
        row["Home"]["Gender"] = None
        with self.assertRaises(ValueError):
            s.senior_fixtures([row])

    def test_unnamed_scheduled_placeholders_are_not_match_witnesses(self):
        row = api_row()
        row.update(Home=None, Away=None, MatchStatus=1)
        self.assertEqual(s.senior_fixtures([row]), [])
        row["MatchStatus"] = 0
        with self.assertRaises(ValueError):
            s.senior_fixtures([row])

    def test_known_club_or_youth_competition_excludes_placeholders(self):
        row = api_row()
        row["IdCompetition"] = "youth"
        row["Home"]["AgeType"] = row["Away"]["AgeType"] = 5
        unknown = {**row, "IdMatch": "2", "Home": None, "Away": None}
        self.assertEqual(s.senior_fixtures([row, unknown]), [])


class CorrectionsTests(unittest.TestCase):
    def test_exact_exclusion_and_identity_change(self):
        f = fixture()
        c = {"id": "test", "date": "2026-10-06", "teams": ["USA", "Canada"],
             "action": "exclude", "source": "https://federation.example/report", "reason": "U23"}
        self.assertEqual(s.correct_fixtures([f], {"fixture_corrections": [c]}), [])
        with self.assertRaises(ValueError):
            s.correct_fixtures([fixture(away="Mexico")], {"fixture_corrections": [c]})

    def test_reschedule_still_detects_missing_after_new_deadline(self):
        c = {"id": "test", "date": "2026-11-04", "teams": ["Bangladesh", "Sri Lanka"],
             "action": "reschedule", "new_date": "2026-11-11",
             "source": "https://federation.example/schedule", "reason": "Revised"}
        f = fixture("2026-11-04", "Bangladesh", "Sri Lanka", 1)
        corrected = s.correct_fixtures([f], {"fixture_corrections": [c]})[0]
        self.assertEqual(corrected["date"], date(2026, 11, 11))
        policy = PolicyTests()
        policy.setUp()
        policy.fixtures.append(corrected)
        self.assertFalse(policy.evaluate("2026-11-14", latest="2026-11-14")["publish_allowed"])
        f["status"] = 0
        with self.assertRaises(ValueError):
            s.correct_fixtures([f], {"fixture_corrections": [c]})

    def test_supplement_merge_catchup_conflict_and_provenance(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            raw, supplement = root / "results.csv", root / "supplement.json"
            raw.write_text(InputTests.csv)
            addition = {"date": "2026-11-05", "home_team": "Pakistan", "away_team": "India",
                        "home_score": "2", "away_score": "3", "tournament": "SAFF Championship",
                        "city": "Dhaka", "country": "Bangladesh", "neutral": "TRUE",
                        "source": "https://federation.example/result"}
            payload = {"schema_version": 1, "reviewed_on": "2026-11-06", "results": [addition]}
            supplement.write_text(json.dumps(payload))
            rows, provenance = s.merged_result_rows(raw, supplement, date(2026, 11, 6))
            self.assertEqual(len(rows), 2)
            self.assertEqual(provenance, {"source_rows_total": 1,
                                         "source_data_through": "2026-10-06", "supplemental_rows": 1})
            # Upstream catches up with reversed home/away order and equal scores.
            raw.write_text(InputTests.csv + "2026-11-05,India,Pakistan,3,2,SAFF Championship,Dhaka,Bangladesh,TRUE\n")
            rows, provenance = s.merged_result_rows(raw, supplement, date(2026, 11, 6))
            self.assertEqual(len(rows), 2)
            self.assertEqual(provenance["supplemental_rows"], 0)
            raw.write_text(InputTests.csv + "2026-11-05,India,Pakistan,4,2,SAFF Championship,Dhaka,Bangladesh,TRUE\n")
            with self.assertRaisesRegex(ValueError, "conflict"):
                s.merged_result_rows(raw, supplement, date(2026, 11, 6))
            raw.write_text(InputTests.csv)
            for field, value in (("source", ""), ("date", "2026-11-07"),
                                 ("home_score", "-2"), ("neutral", "maybe")):
                changed = {**payload, "results": [{**addition, field: value}]}
                supplement.write_text(json.dumps(changed))
                with self.subTest(field=field), self.assertRaises(ValueError):
                    s.merged_result_rows(raw, supplement, date(2026, 11, 6))

    def test_supplement_cannot_mask_primary_regression(self):
        policy = PolicyTests()
        policy.setUp()
        meta = {"rows_total": 1, "data_through": "2026-10-06", "as_of": "2026-11-06",
                "teams_profiled": 257, "source_rows_total": 0, "source_data_through": "2026-10-05"}
        previous = {"rows_total": 1, "data_through": "2026-10-06"}
        with self.assertRaisesRegex(ValueError, "Primary source regressed"):
            s.evaluate(policy.matches, meta, previous, policy.calendar, policy.fixtures, date(2026, 11, 6))


class InputTests(unittest.TestCase):
    header = "date,home_team,away_team,home_score,away_score,tournament,city,country,neutral\n"
    csv = header + "2026-10-06,USA,Canada,1,0,Friendly,Toronto,Canada,FALSE\n"

    def test_csv_validation(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "results.csv"
            path.write_text(self.csv)
            self.assertEqual(len(s.read_results(path, date(2026, 11, 6))), 1)
            for body in ("", "date\n2026-10-06\n", self.csv.replace("1,0", ",0"),
                         self.csv.replace("1,0", "-1,0"), self.csv.replace("1,0", "1.5,0"),
                         self.csv.replace("2026-10-06", "2027-10-06"),
                         self.csv.replace("2026-10-06", "not-a-date"),
                         # short row (missing trailing columns) and over-long row
                         self.header + "2026-10-06,USA,Canada,1,0\n",
                         self.csv.replace("FALSE\n", "FALSE,extra\n"),
                         # old five-column layout no longer satisfies the distiller's needs
                         "date,home_team,away_team,home_score,away_score\n2026-10-06,USA,Canada,1,0\n",
                         self.csv.replace("Friendly", ""), self.csv.replace("FALSE", "maybe")):
                path.write_text(body)
                with self.subTest(body=body), self.assertRaises(ValueError):
                    s.read_results(path, date(2026, 11, 6))

    def test_failed_download_does_not_reuse_cached_results(self):
        with tempfile.TemporaryDirectory() as folder:
            raw = Path(folder)
            (raw / "results.csv").write_text(self.csv)
            with patch.object(pull, "download", side_effect=ValueError("both branches failed")):
                with self.assertRaises(ValueError):
                    pull.pull(raw)
            self.assertEqual((raw / "results.csv").read_text(), self.csv)

    def test_bad_download_preserves_previous_file(self):
        with tempfile.TemporaryDirectory() as folder:
            raw = Path(folder)
            (raw / "results.csv").write_text(self.csv)
            with patch.object(pull, "download", return_value=(b"invalid", "url")):
                with self.assertRaises(ValueError):
                    pull.pull(raw)
            self.assertEqual((raw / "results.csv").read_text(), self.csv)
            self.assertFalse((raw / "results.csv.tmp").exists())

    def test_download_fallback_and_total_failure(self):
        # A retryable error is retried up to the per-URL cap on each branch, then
        # the next branch is tried; both exhausted is a ValueError, never a cached file.
        with patch.object(pull, "urlopen", side_effect=OSError("offline")) as fetch, \
                patch.object(transport.time, "sleep"):
            with self.assertRaisesRegex(ValueError, "Cannot download"):
                pull.download("results.csv")
            self.assertEqual(fetch.call_count, 2 * transport.MAX_ATTEMPTS_PER_URL)

    def test_download_permanent_404_falls_through_to_next_branch(self):
        calls = []

        def opener(request, timeout):
            calls.append(request.full_url)
            if "/master/" in request.full_url:
                raise HTTPError(request.full_url, 404, "Not Found", {}, None)
            return FakeResponse(b"date,home_team\n")

        with patch.object(pull, "urlopen", opener):
            body, url = pull.download("results.csv")
        self.assertEqual(body, b"date,home_team\n")
        self.assertTrue(url.endswith("/main/results.csv"))
        self.assertEqual(len(calls), 2)  # 404 is permanent: one request per branch

    def test_download_truncated_then_recovers(self):
        attempts = []

        def opener(request, timeout):
            attempts.append(1)
            if len(attempts) == 1:
                raise IncompleteRead(b"partial", 100)
            return FakeResponse(InputTests.csv.encode())

        with patch.object(pull, "urlopen", opener), patch.object(transport.time, "sleep"):
            body, _ = pull.download("results.csv")
        self.assertEqual(body, InputTests.csv.encode())
        self.assertEqual(len(attempts), 2)

    def test_pull_cli_failure_writes_pull_stage_diagnostic(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "status.json"
            with patch.object(pull, "download", side_effect=ValueError("both branches failed")):
                self.assertEqual(pull.main(raw=Path(folder), output=output), 1)
            record = json.loads(output.read_text())
            self.assertEqual(record["stage"], "pull")
            self.assertEqual(record["error_category"], "validation")
            self.assertFalse(record["publish_allowed"])
            self.assertIn("transport", record)

    def test_cli_failure_writes_diagnostics_and_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "status.json"
            missing = str(Path(folder) / "missing.json")
            self.assertEqual(s.main(["--previous-meta", missing, "--calendar", missing,
                                     "--output", str(output)]), 1)
            record = json.loads(output.read_text())
            self.assertFalse(record["publish_allowed"])
            self.assertEqual(record["stage"], "verify")
            self.assertEqual(record["error_category"], "io")
            self.assertFalse(record["last_good"]["available"])
            self.assertEqual(record["fixture_queries"], [])
            self.assertIn("transport", record)


if __name__ == "__main__":
    unittest.main()
