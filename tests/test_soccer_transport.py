"""Bounded transport: retry classes, backoff/Retry-After bounds, budgets, replay of
the 2026-11-08 truncated-response failure (run 42436558372)."""
import json
import socket
import ssl
import sys
import tempfile
import unittest
from datetime import date
from http.client import IncompleteRead, RemoteDisconnected
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import soccer_diagnostics as diag
import soccer_freshness as s
import soccer_transport as t


class FakeResponse:
    def __init__(self, body, status=200, headers=None):
        self.body, self.status, self.headers = body, status, headers or {}

    def read(self):
        return self.body

    def getcode(self):
        return self.status

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class Clock:
    """Deterministic monotonic clock; sleeps advance it."""

    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(round(seconds, 3))
        self.now += seconds


def scripted(*outcomes):
    """Build an opener that yields each outcome in turn (exception instances raise)."""
    calls = []

    def opener(request, timeout):
        calls.append((request.full_url, timeout))
        outcome = outcomes[min(len(calls) - 1, len(outcomes) - 1)]
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome
    opener.calls = calls
    return opener


def fetch(opener, clock=None, budget=None, **kw):
    clock = clock or Clock()
    budget = budget or t.Budget(max_requests=50, max_elapsed_s=600, clock=clock)
    kw.setdefault("jitter", lambda: 1.0)
    return t.fetch_bytes("https://example.test/path?x=1", budget, opener=opener,
                         sleep=clock.sleep, **kw), budget, clock


class RetryClassTests(unittest.TestCase):
    def test_truncated_then_recovers(self):
        opener = scripted(IncompleteRead(b"half", 10), FakeResponse(b"full body"))
        (body, info), budget, clock = fetch(opener)
        self.assertEqual(body, b"full body")
        self.assertEqual(info["attempts"], 2)
        self.assertEqual(clock.sleeps, [1.0])
        self.assertEqual([h["outcome"] for h in budget.history], ["error", "ok"])
        self.assertEqual(budget.history[0]["error"], "incomplete_read")

    def test_truncated_on_every_attempt_is_bounded(self):
        opener = scripted(IncompleteRead(b"", 1))
        with self.assertRaises(t.TransportError) as ctx:
            fetch(opener)
        self.assertEqual(ctx.exception.category, "transport")
        self.assertEqual(ctx.exception.attempts, t.MAX_ATTEMPTS_PER_URL)
        self.assertEqual(len(opener.calls), t.MAX_ATTEMPTS_PER_URL)
        self.assertEqual(len(ctx.exception.history), t.MAX_ATTEMPTS_PER_URL)

    def test_content_length_mismatch_is_treated_as_truncation(self):
        opener = scripted(FakeResponse(b"abc", headers={"Content-Length": "10"}),
                          FakeResponse(b"abcdefghij", headers={"Content-Length": "10"}))
        (body, info), _, _ = fetch(opener)
        self.assertEqual(body, b"abcdefghij")
        self.assertEqual(info["attempts"], 2)

    def test_empty_body_is_retried_not_returned(self):
        opener = scripted(FakeResponse(b""), FakeResponse(b"ok"))
        (body, _), _, _ = fetch(opener)
        self.assertEqual(body, b"ok")

    def test_timeout_reset_and_remote_disconnect_retry(self):
        for exc in (socket.timeout("timed out"), TimeoutError(), ConnectionResetError(104, "reset"),
                    RemoteDisconnected("closed"), URLError(socket.timeout("t")),
                    URLError(ConnectionRefusedError())):
            with self.subTest(exc=type(exc).__name__):
                (body, info), _, _ = fetch(scripted(exc, FakeResponse(b"ok")))
                self.assertEqual((body, info["attempts"]), (b"ok", 2))

    def test_retryable_http_statuses_retry(self):
        for code in sorted(t.RETRYABLE_STATUS):
            with self.subTest(code=code):
                err = HTTPError("https://example.test/path", code, "x", {}, None)
                (body, info), _, _ = fetch(scripted(err, FakeResponse(b"ok")))
                self.assertEqual((body, info["attempts"]), (b"ok", 2))

    def test_permanent_4xx_not_retried(self):
        for code in (400, 401, 403, 404, 410, 422):
            with self.subTest(code=code):
                opener = scripted(HTTPError("https://example.test/path", code, "x", {}, None))
                with self.assertRaises(t.TransportError) as ctx:
                    fetch(opener)
                self.assertEqual(ctx.exception.category, "http_permanent")
                self.assertEqual(len(opener.calls), 1)

    def test_tls_verification_failure_not_retried(self):
        opener = scripted(URLError(ssl.SSLCertVerificationError("certificate verify failed")))
        with self.assertRaises(t.TransportError) as ctx:
            fetch(opener)
        self.assertEqual(ctx.exception.category, "tls")
        self.assertEqual(len(opener.calls), 1)

    def test_invalid_json_after_complete_response_is_not_retried(self):
        opener = scripted(FakeResponse(b"<html>not json</html>"))
        budget = t.Budget(max_requests=10, max_elapsed_s=60, clock=Clock())
        with self.assertRaises(t.InvalidResponse):
            t.fetch_json("https://example.test/x", budget, opener=opener, sleep=lambda _: None)
        self.assertEqual(len(opener.calls), 1)
        self.assertIsInstance(t.InvalidResponse("x"), ValueError)


class BoundsTests(unittest.TestCase):
    def test_backoff_doubles_with_cap(self):
        opener = scripted(IncompleteRead(b"", 1))
        with patch.object(t, "MAX_ATTEMPTS_PER_URL", 8):
            with self.assertRaises(t.TransportError):
                fetch(opener, max_attempts=8)
        # sleeps happen between attempts only: 7 sleeps, capped at 20s
        clock = Clock()
        opener = scripted(IncompleteRead(b"", 1))
        with self.assertRaises(t.TransportError):
            fetch(opener, clock=clock, max_attempts=8)
        self.assertEqual(clock.sleeps, [1.0, 2.0, 4.0, 8.0, 16.0, 20.0, 20.0])

    def test_jitter_applied(self):
        clock = Clock()
        with self.assertRaises(t.TransportError):
            fetch(scripted(IncompleteRead(b"", 1)), clock=clock, max_attempts=2, jitter=lambda: 0.75)
        self.assertEqual(clock.sleeps, [0.75])

    def test_retry_after_seconds_honoured_and_capped(self):
        clock = Clock()
        err = HTTPError("u", 429, "slow", {"Retry-After": "5"}, None)
        (body, _), _, _ = fetch(scripted(err, FakeResponse(b"ok")), clock=clock)
        self.assertEqual(clock.sleeps, [5.0])
        clock = Clock()
        err = HTTPError("u", 503, "slow", {"Retry-After": "900"}, None)
        (body, _), _, _ = fetch(scripted(err, FakeResponse(b"ok")), clock=clock)
        self.assertEqual(clock.sleeps, [t.RETRY_AFTER_CAP_S])

    def test_retry_after_http_date_and_garbage(self):
        self.assertEqual(t._retry_after_seconds({"Retry-After": "Thu, 01 Jan 1970 00:00:00 GMT"}), 0.0)
        self.assertIsNone(t._retry_after_seconds({"Retry-After": "soon"}))
        self.assertIsNone(t._retry_after_seconds({}))

    def test_request_budget_exhaustion_raises_before_issuing(self):
        clock = Clock()
        budget = t.Budget(max_requests=3, max_elapsed_s=600, clock=clock)
        opener = scripted(IncompleteRead(b"", 1))
        with self.assertRaises(t.TransportError) as ctx:
            fetch(opener, clock=clock, budget=budget)
        self.assertEqual(ctx.exception.category, "budget")
        self.assertEqual(len(opener.calls), 3)
        self.assertEqual(budget.requests, 3)

    def test_elapsed_budget_refuses_waiting_past_deadline(self):
        clock = Clock()
        budget = t.Budget(max_requests=50, max_elapsed_s=2.5, clock=clock)
        opener = scripted(IncompleteRead(b"", 1))
        with self.assertRaises(t.TransportError) as ctx:
            fetch(opener, clock=clock, budget=budget)
        self.assertEqual(ctx.exception.category, "budget")
        self.assertEqual(clock.sleeps, [1.0])          # second wait (2s) would exceed 2.5s
        self.assertEqual(len(opener.calls), 2)

    def test_elapsed_budget_exhausted_before_request(self):
        clock = Clock()
        budget = t.Budget(max_requests=50, max_elapsed_s=10, clock=clock)
        clock.now = 11
        with self.assertRaises(t.TransportError) as ctx:
            fetch(scripted(FakeResponse(b"ok")), clock=clock, budget=budget)
        self.assertEqual(ctx.exception.category, "budget")

    def test_timeout_never_exceeds_remaining_budget(self):
        clock = Clock()
        budget = t.Budget(max_requests=5, max_elapsed_s=10, clock=clock)
        clock.now = 7
        opener = scripted(FakeResponse(b"ok"))
        fetch(opener, clock=clock, budget=budget, timeout=45)
        self.assertEqual(opener.calls[0][1], 3.0)

    def test_budget_rejects_nonsense(self):
        with self.assertRaises(ValueError):
            t.Budget(0, 10)
        with self.assertRaises(ValueError):
            t.Budget(1, 0)

    def test_budget_summary_counts_physical_requests(self):
        (body, _), budget, _ = fetch(scripted(IncompleteRead(b"", 1), FakeResponse(b"ok")))
        summary = budget.summary()
        self.assertEqual(summary["physical_requests"], 2)
        self.assertEqual(len(summary["attempt_history"]), 2)


class SanitizeTests(unittest.TestCase):
    def test_secrets_redacted_and_userinfo_dropped(self):
        url = "https://user:pw@api.example/v1?from=a&token=abc&x-apisports-key=zzz&apikey=k"
        shown = t.sanitize_url(url)
        self.assertNotIn("pw", shown)
        self.assertNotIn("abc", shown)
        self.assertNotIn("zzz", shown)
        self.assertIn("from=a", shown)
        self.assertEqual(shown.count("REDACTED"), 3)


def api_row(match_id, day):
    def team(name):
        return {"TeamType": 1, "AgeType": 7, "Gender": 1, "FootballType": 0,
                "TeamName": [{"Locale": "en-GB", "Description": name}]}
    return {"IdMatch": match_id, "Date": day, "LocalDate": day, "IdCompetition": "c",
            "Home": team("USA"), "Away": team("Canada"), "MatchStatus": 0}


class FifaReplayTests(unittest.TestCase):
    """Replay of run 42436558372: a later split page raised IncompleteRead."""

    def make_fetch(self, truncate_times):
        """Top-level query saturates, forcing a split; the second half truncates N times."""
        state = {"truncations": 0, "urls": []}

        def fetch(url):
            state["urls"].append(url)
            q = parse_qs(urlparse(url).query)
            a, b = q["from"][0], q["to"][0]
            if a == "2026-11-01T00:00:00Z" and b == "2026-11-02T23:59:59Z":
                return {"Results": [], "ContinuationToken": "more"}
            if a.startswith("2026-11-02") and state["truncations"] < truncate_times:
                state["truncations"] += 1
                raise IncompleteRead(b"x" * 305950, 1000)
            rows = [api_row("m1", "2026-11-01T12:00:00Z")] if a.startswith("2026-11-01") else \
                   [api_row("m2", "2026-11-02T12:00:00Z")]
            return {"Results": rows, "ContinuationToken": None}
        fetch.state = state
        return fetch

    def test_unbounded_truncation_on_later_page_fails_but_keeps_query_history(self):
        fetch = self.make_fetch(truncate_times=10 ** 6)
        history = []
        with self.assertRaises(IncompleteRead):
            s.fetch_fixtures(date(2026, 11, 1), date(2026, 11, 2), fetch, history=history)
        # 3 logical queries were attempted (top, first half, second half) and are retained
        self.assertEqual(len(history), 3)
        self.assertTrue(history[-1].startswith(s.FIFA_URL))
        self.assertIn("from=2026-11-02T00%3A00%3A00Z", history[-1])

    def test_replay_through_transport_recovers_and_returns_complete_collection(self):
        """Same shape as production: get_json -> fetch_json -> retries -> recovery."""
        clock = Clock()
        budget = t.Budget(max_requests=s.FIFA_MAX_REQUESTS, max_elapsed_s=s.FIFA_MAX_ELAPSED_S, clock=clock)
        truncations = {"n": 0}

        def opener(request, timeout):
            q = parse_qs(urlparse(request.full_url).query)
            a, b = q["from"][0], q["to"][0]
            if a == "2026-11-01T00:00:00Z" and b == "2026-11-02T23:59:59Z":
                return FakeResponse(json.dumps({"Results": [], "ContinuationToken": "more"}).encode())
            if a.startswith("2026-11-02") and truncations["n"] < 2:
                truncations["n"] += 1
                raise IncompleteRead(b"x" * 305950, 1000)
            rows = [api_row("m1", "2026-11-01T12:00:00Z")] if a.startswith("2026-11-01") else \
                   [api_row("m2", "2026-11-02T12:00:00Z")]
            return FakeResponse(json.dumps({"Results": rows, "ContinuationToken": None}).encode())

        history = []
        with patch.object(t, "urlopen", opener), patch.object(t.time, "sleep", clock.sleep), \
                patch.object(t.random, "uniform", lambda a, b: 1.0):
            rows, urls = s.fetch_fixtures(date(2026, 11, 1), date(2026, 11, 2),
                                          fetch=lambda u: s.get_json(u, budget), history=history)
        self.assertEqual(sorted(r["IdMatch"] for r in rows), ["m1", "m2"])
        self.assertEqual(len(urls), 3)                  # logical queries
        self.assertEqual(budget.requests, 5)            # 3 queries + 2 retries
        self.assertEqual(clock.sleeps, [1.0, 2.0])
        self.assertEqual(sum(h["outcome"] == "error" for h in budget.history), 2)

    def test_replay_exhausts_attempts_through_transport_without_partial_result(self):
        clock = Clock()
        budget = t.Budget(max_requests=s.FIFA_MAX_REQUESTS, max_elapsed_s=s.FIFA_MAX_ELAPSED_S, clock=clock)

        def opener(request, timeout):
            q = parse_qs(urlparse(request.full_url).query)
            a, b = q["from"][0], q["to"][0]
            if a == "2026-11-01T00:00:00Z" and b == "2026-11-02T23:59:59Z":
                return FakeResponse(json.dumps({"Results": [], "ContinuationToken": "more"}).encode())
            if a.startswith("2026-11-02"):
                raise IncompleteRead(b"", 1)
            return FakeResponse(json.dumps(
                {"Results": [api_row("m1", "2026-11-01T12:00:00Z")], "ContinuationToken": None}).encode())

        history = []
        with patch.object(t, "urlopen", opener), patch.object(t.time, "sleep", clock.sleep):
            with self.assertRaises(t.TransportError) as ctx:
                s.fetch_fixtures(date(2026, 11, 1), date(2026, 11, 2),
                                 fetch=lambda u: s.get_json(u, budget), history=history)
        self.assertEqual(ctx.exception.attempts, t.MAX_ATTEMPTS_PER_URL)
        self.assertEqual(len(history), 3)
        self.assertEqual(budget.requests, 2 + t.MAX_ATTEMPTS_PER_URL)

    def test_physical_request_budget_caps_nested_retries(self):
        """128 logical queries x 4 attempts must not reach 512 requests."""
        clock = Clock()
        budget = t.Budget(max_requests=s.FIFA_MAX_REQUESTS, max_elapsed_s=10 ** 6, clock=clock)
        opener = scripted(IncompleteRead(b"", 1))
        categories = []
        with patch.object(t, "urlopen", opener), patch.object(t.time, "sleep", clock.sleep):
            for _ in range(200):   # simulate many logical queries each exhausting its retries
                try:
                    s.get_json("https://api.fifa.com/api/v3/calendar/matches?q=1", budget)
                except t.TransportError as exc:
                    categories.append(exc.category)
                    if exc.category == "budget":
                        break
        self.assertEqual(categories[-1], "budget")
        self.assertEqual(len(opener.calls), s.FIFA_MAX_REQUESTS)
        self.assertEqual(categories.count("transport"), s.FIFA_MAX_REQUESTS // t.MAX_ATTEMPTS_PER_URL)


class VerifyCliDiagnosticsTests(unittest.TestCase):
    """main() writes a verify-stage record for every failure class, including the
    IncompleteRead class that escaped the handler on 2026-11-08."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        root = Path(self.folder.name)
        today = date.today()
        self.previous = root / "previous.json"
        self.previous.write_text(json.dumps({"data_through": "2026-10-06", "rows_total": 1,
                                             "source_data_through": "2026-10-06", "source_rows_total": 1}))
        self.calendar = root / "calendar.json"
        self.calendar.write_text(json.dumps({
            "schema_version": 1, "reviewed_on": "2026-10-01", "valid_from": "2020-01-01",
            "valid_through": "2099-12-31", "sources": ["https://x"],
            "periods": [{"start": "2026-09-21", "end": "2026-10-06", "name": "Oct"}]}))
        self.results = root / "results.csv"
        self.results.write_text("date,home_team,away_team,home_score,away_score,tournament,city,country,neutral\n"
                                f"{today.isoformat()},USA,Canada,1,0,Friendly,Toronto,Canada,FALSE\n")
        self.supplements = root / "supp.json"
        self.supplements.write_text(json.dumps({"schema_version": 1, "reviewed_on": "2026-10-01", "results": []}))
        teams = {f"Team {i}": {"gp": 1, "w": 1, "d": 0, "l": 0} for i in range(200)}
        meta = {"as_of": today.isoformat(), "data_through": today.isoformat(), "rows_total": 1,
                "source_rows_total": 1, "source_data_through": today.isoformat(),
                "supplemental_rows": 0, "teams_profiled": len(teams)}
        self.meta = root / "meta.json"
        self.meta.write_text(json.dumps(meta))
        self.profiles = root / "team_profiles.json"
        self.profiles.write_text(json.dumps({"as_of": meta["as_of"], "data_through": meta["data_through"],
                                             "teams": teams}))
        self.rates = root / "wc.json"
        self.rates.write_text(json.dumps({"as_of": meta["as_of"]}))
        self.output = root / "status.json"
        self.argv = ["--previous-meta", str(self.previous), "--calendar", str(self.calendar),
                     "--results", str(self.results), "--supplements", str(self.supplements),
                     "--meta", str(self.meta), "--profiles", str(self.profiles),
                     "--base-rates", str(self.rates), "--output", str(self.output)]

    def tearDown(self):
        self.folder.cleanup()

    def run_main(self, opener):
        clock = Clock()
        with patch.object(t, "urlopen", opener), patch.object(t.time, "sleep", clock.sleep), \
                patch.dict("os.environ", {"GITHUB_SHA": "deadbeef", "GITHUB_RUN_ID": "42"}):
            code = s.main(self.argv)
        return code, json.loads(self.output.read_text())

    def test_incomplete_read_on_every_attempt_writes_verify_diagnostic(self):
        opener = scripted(IncompleteRead(b"x" * 305950, 1))
        code, record = self.run_main(opener)
        self.assertEqual(code, 1)
        self.assertEqual(record["stage"], "verify")
        self.assertEqual(record["error_category"], "transport:transport")
        self.assertEqual(record["error_type"], "TransportError")
        self.assertEqual(record["failed_url_attempts"], t.MAX_ATTEMPTS_PER_URL)
        self.assertEqual(record["transport"]["physical_requests"], t.MAX_ATTEMPTS_PER_URL)
        self.assertEqual(len(record["fixture_queries"]), 1)
        self.assertEqual(record["commit"], "deadbeef")
        self.assertEqual(record["run_id"], "42")
        self.assertEqual(record["last_good"]["data_through"], "2026-10-06")
        self.assertFalse(record["publish_allowed"])
        self.assertTrue(record["started_at"] <= record["finished_at"])

    def test_unexpected_exception_still_writes_diagnostic(self):
        row = api_row("m", f"{date.today().isoformat()}T12:00:00Z")
        payload = json.dumps({"Results": [row], "ContinuationToken": None}).encode()
        with patch.object(s, "senior_fixtures", side_effect=RuntimeError("something nobody anticipated")):
            code, record = self.run_main(scripted(FakeResponse(payload)))
        self.assertEqual(code, 1)
        self.assertEqual(record["error_category"], "unexpected:RuntimeError")
        self.assertTrue(any("RuntimeError" in line for line in record["traceback"]))

    def test_invalid_json_body_is_invalid_response(self):
        code, record = self.run_main(scripted(FakeResponse(b"<html>")))
        self.assertEqual(code, 1)
        self.assertEqual(record["error_category"], "invalid_response")
        self.assertEqual(record["transport"]["physical_requests"], 1)

    def test_distillate_metadata_mismatch_blocks_before_any_request(self):
        profiles = json.loads(self.profiles.read_text())
        del profiles["teams"]["Team 0"]
        self.profiles.write_text(json.dumps(profiles))
        opener = scripted(FakeResponse(b"{}"))
        code, record = self.run_main(opener)
        self.assertEqual(code, 1)
        self.assertEqual(record["error_category"], "validation")
        self.assertIn("team count", record["errors"][0])
        self.assertEqual(len(opener.calls), 0)

    def test_successful_verify_carries_stage_and_transport_fields(self):
        row = api_row("m", f"{date.today().isoformat()}T12:00:00Z")
        payload = json.dumps({"Results": [row], "ContinuationToken": None}).encode()
        code, record = self.run_main(scripted(FakeResponse(payload)))
        self.assertEqual(code, 0, record.get("errors"))
        self.assertEqual(record["stage"], "verify")
        self.assertTrue(record["publish_allowed"])
        self.assertEqual(record["transport"]["physical_requests"], 1)
        self.assertEqual(record["last_good"]["rows_total"], 1)


class DistillateValidationTests(unittest.TestCase):
    def test_non_finite_values_rejected(self):
        meta = {"as_of": "2026-11-08", "data_through": "2026-11-05", "teams_profiled": 1}
        with tempfile.TemporaryDirectory() as folder:
            p, r = Path(folder) / "p.json", Path(folder) / "r.json"
            r.write_text(json.dumps({"as_of": "2026-11-08"}))
            p.write_text(json.dumps({"as_of": "2026-11-08", "data_through": "2026-11-05",
                                     "teams": {"A": {"gp": 1, "w": 1, "d": 0, "l": 0, "gf_pg": float("nan")}}}))
            with self.assertRaises(ValueError):
                s.validate_distillates(meta, p, r)
            p.write_text(json.dumps({"as_of": "2026-11-08", "data_through": "2026-11-05",
                                     "teams": {"A": {"gp": 2, "w": 1, "d": 0, "l": 0}}}))
            with self.assertRaisesRegex(ValueError, "W/D/L"):
                s.validate_distillates(meta, p, r)
            p.write_text(json.dumps({"as_of": "2026-11-07", "data_through": "2026-11-05",
                                     "teams": {"A": {"gp": 1, "w": 1, "d": 0, "l": 0}}}))
            with self.assertRaisesRegex(ValueError, "as_of"):
                s.validate_distillates(meta, p, r)


class DiagnosticsCliTests(unittest.TestCase):
    def test_if_missing_writes_gap_record_once(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "status.json"
            self.assertEqual(diag.main(["--if-missing", "--stage", "workflow", "--message", "none",
                                        "--output", str(out), "--previous-meta", str(out)]), 0)
            record = json.loads(out.read_text())
            self.assertEqual(record["error_category"], "diagnostic_gap")
            self.assertFalse(record["publish_allowed"])
            self.assertFalse(record["last_good"]["available"])
            out.write_text(json.dumps({"state": "ok", "publish_allowed": True}))
            diag.main(["--if-missing", "--stage", "workflow", "--message", "none", "--output", str(out)])
            self.assertEqual(json.loads(out.read_text())["state"], "ok")

    def test_annotate_marks_publish_failure_without_flipping_verdict(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "status.json"
            out.write_text(json.dumps({"stage": "verify", "state": "active", "publish_allowed": True}))
            diag.main(["--annotate", "--stage", "publish", "--message", "push failed", "--output", str(out)])
            record = json.loads(out.read_text())
            self.assertTrue(record["publish_allowed"])   # the verify verdict is preserved ...
            self.assertFalse(record["published"])         # ... but publication is recorded as not done
            self.assertEqual(record["stage_outcomes"]["publish"]["message"], "push failed")

    def test_classification(self):
        self.assertEqual(diag.classify_exception(ValueError("x")), "validation")
        self.assertEqual(diag.classify_exception(KeyError("x")), "schema")
        self.assertEqual(diag.classify_exception(OSError("x")), "io")
        self.assertEqual(diag.classify_exception(RuntimeError("x")), "unexpected:RuntimeError")
        err = t.TransportError("x", category="budget", url="u", attempts=1, history=[])
        self.assertEqual(diag.classify_exception(err), "transport:budget")

    def test_write_record_rejects_nan(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                diag.write_record({"x": float("nan")}, Path(folder) / "s.json")


if __name__ == "__main__":
    unittest.main()
