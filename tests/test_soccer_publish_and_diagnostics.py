"""Rosie review items 1, 3, 4: run-scoped diagnostics from checkout, typed pull
failures, and evidence-based publication verification."""
import hashlib
import json
import ssl
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import pull_soccer as pull
import soccer_diagnostics as diag
import soccer_publish_verify as pv
import soccer_transport as t


class FakeResponse:
    def __init__(self, body, status=200, headers=None):
        self.body, self.status, self.headers = body, status, headers or {}

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


# ---------------------------------------------------------------- item 3: pull

class PullTypedErrorTests(unittest.TestCase):
    def run_pull_main(self, opener):
        with tempfile.TemporaryDirectory() as folder:
            raw = Path(folder) / "raw"
            raw.mkdir()
            (raw / "MANIFEST.json").write_text(json.dumps({"files": {"results.csv": {}}}))
            out = Path(folder) / "status.json"
            with patch.object(pull, "urlopen", opener), patch.object(t.time, "sleep", lambda s: None):
                code = pull.main(raw=raw, output=out)
            return code, json.loads(out.read_text())

    def test_permanent_404_on_both_branches_is_http_permanent_not_validation(self):
        def opener(request, timeout):
            raise HTTPError(request.full_url, 404, "Not Found", {}, None)
        code, record = self.run_pull_main(opener)
        self.assertEqual(code, 1)
        self.assertEqual(record["stage"], "pull")
        self.assertEqual(record["error_category"], "transport:http_permanent")
        self.assertEqual(record["error_type"], "DownloadError")
        self.assertTrue(record["failed_url"].endswith("/main/results.csv"))
        self.assertEqual(record["failed_url_attempts"], 1)
        self.assertEqual([f["branch"] for f in record["download_failures"]], ["master", "main"])
        self.assertTrue(all(f["category"] == "http_permanent" and f["attempts"] == 1
                            for f in record["download_failures"]))
        self.assertEqual(record["transport"]["physical_requests"], 2)

    def test_tls_failure_is_typed_and_not_retried(self):
        def opener(request, timeout):
            raise URLError(ssl.SSLCertVerificationError("certificate verify failed"))
        code, record = self.run_pull_main(opener)
        self.assertEqual(record["error_category"], "transport:tls")
        self.assertEqual(record["transport"]["physical_requests"], 2)   # one per branch
        self.assertTrue(all(f["category"] == "tls" for f in record["download_failures"]))

    def test_budget_exhaustion_stops_before_second_branch(self):
        def opener(request, timeout):
            raise ConnectionResetError(104, "reset")
        with patch.object(pull, "PULL_MAX_REQUESTS", 3):
            code, record = self.run_pull_main(opener)
        self.assertEqual(record["error_category"], "transport:budget")
        self.assertEqual(record["transport"]["physical_requests"], 3)
        self.assertEqual(len(record["download_failures"]), 1)       # master only; no budget for main
        self.assertEqual(record["download_failures"][0]["category"], "budget")

    def test_download_error_is_a_value_error_for_optional_file_path(self):
        err = pull.DownloadError("shootouts.csv", [{"branch": "master", "url": "u", "category": "transport",
                                                     "attempts": 4, "error": "x"}], [])
        self.assertIsInstance(err, ValueError)
        self.assertIsInstance(err, t.TransportError)
        self.assertEqual(err.category, "transport")
        self.assertIn("Cannot download shootouts.csv", str(err))

    def test_invalid_csv_after_good_download_stays_validation(self):
        def opener(request, timeout):
            return FakeResponse(b"garbage")
        code, record = self.run_pull_main(opener)
        self.assertEqual(record["error_category"], "validation")


# ------------------------------------------------------- item 1: diagnostics

class RunScopedDiagnosticsTests(unittest.TestCase):
    PRIOR_SUCCESS = {"schema_version": 2, "stage": "verify", "state": "awaiting_results",
                     "publish_allowed": True, "run_id": "111", "checked_at": "2026-11-07T20:38:50+00:00"}

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.out = Path(self.folder.name) / "status.json"
        self.prev = Path(self.folder.name) / "meta.json"
        self.prev.write_text(json.dumps({"data_through": "2026-11-05", "rows_total": 1}))
        self.out.write_text(json.dumps(self.PRIOR_SUCCESS))
        self.env = patch.dict("os.environ", {"GITHUB_RUN_ID": "222", "GITHUB_SHA": "abc"})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.folder.cleanup()

    def cli(self, *args):
        return diag.main([*args, "--output", str(self.out), "--previous-meta", str(self.prev)])

    def test_init_replaces_committed_prior_success(self):
        self.assertEqual(self.cli("--init", "--stage", "workflow", "--message", "start"), 0)
        rec = json.loads(self.out.read_text())
        self.assertEqual(rec["state"], "in_progress")
        self.assertFalse(rec["publish_allowed"])
        self.assertEqual(rec["run_id"], "222")
        self.assertEqual(rec["superseded_record"]["run_id"], "111")
        self.assertEqual(rec["last_good"]["data_through"], "2026-11-05")

    def test_dependency_install_failure_after_init_yields_gap_not_prior_success(self):
        # checkout -> init -> (pip install fails; no stage runs) -> ensure -> upload
        self.cli("--init", "--stage", "workflow", "--message", "start")
        self.assertEqual(self.cli("--if-missing", "--stage", "workflow", "--message", "no stage reported"), 0)
        rec = json.loads(self.out.read_text())
        self.assertEqual(rec["state"], "blocked")
        self.assertFalse(rec["publish_allowed"])
        self.assertEqual(rec["error_category"], "diagnostic_gap")
        self.assertEqual(rec["run_id"], "222")
        self.assertIsNotNone(rec["started_at"])
        self.assertTrue(any("no stage wrote a result" in e for e in rec["errors"]))

    def test_if_missing_rejects_wrong_run_record(self):
        # init step skipped entirely (e.g. checkout succeeded but the step did not run)
        self.assertEqual(self.cli("--if-missing", "--stage", "workflow", "--message", "gap"), 0)
        rec = json.loads(self.out.read_text())
        self.assertEqual(rec["error_category"], "diagnostic_gap")
        self.assertEqual(rec["rejected_record"], {"reason": "wrong_run", "run_id": "111",
                                                  "stage": "verify",
                                                  "checked_at": "2026-11-07T20:38:50+00:00"})

    def test_if_missing_rejects_malformed_and_schema_mismatch(self):
        self.out.write_text("{not json")
        self.cli("--if-missing", "--stage", "workflow", "--message", "gap")
        self.assertEqual(json.loads(self.out.read_text())["rejected_record"]["reason"], "malformed")
        self.out.write_text(json.dumps({"schema_version": 1, "run_id": "222"}))
        self.cli("--if-missing", "--stage", "workflow", "--message", "gap")
        self.assertEqual(json.loads(self.out.read_text())["rejected_record"]["reason"], "schema_mismatch")

    def test_if_missing_leaves_current_run_stage_record_alone(self):
        current = {**self.PRIOR_SUCCESS, "run_id": "222"}
        self.out.write_text(json.dumps(current))
        self.cli("--if-missing", "--stage", "workflow", "--message", "gap")
        self.assertEqual(json.loads(self.out.read_text()), current)

    def test_annotate_on_wrong_run_record_starts_fresh_and_records_rejection(self):
        self.cli("--annotate", "--stage", "publish", "--message", "push failed")
        rec = json.loads(self.out.read_text())
        self.assertEqual(rec["run_id"], "222")
        self.assertEqual(rec["rejected_record"]["reason"], "wrong_run")
        self.assertEqual(rec["published"], "unknown")
        self.assertNotIn("publish_allowed", rec)   # no verdict invented

    def test_without_run_id_any_well_formed_record_is_current(self):
        with patch.dict("os.environ", {"GITHUB_RUN_ID": ""}):
            rec, rejection = diag.load_current_record(self.out)
        self.assertIsNone(rejection)
        self.assertEqual(rec["run_id"], "111")


# -------------------------------------------------------- item 4: publication

def h(data):
    return hashlib.sha256(data).hexdigest()


class PublishVerifyTests(unittest.TestCase):
    META = b'{"data_through": "2026-11-08"}\n'
    PROFILES = b'{"teams": {}}\n'
    PREV_META = b'{"data_through": "2026-11-05"}\n'

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        root = Path(self.folder.name)
        (root / "distillates/soccer").mkdir(parents=True)
        (root / "distillates/soccer/meta.json").write_bytes(self.META)
        (root / "distillates/soccer/team_profiles.json").write_bytes(self.PROFILES)
        self.prev = root / "prev.json"
        self.prev.write_bytes(self.PREV_META)
        self.root = root
        self.out = root / "status.json"

    def tearDown(self):
        self.folder.cleanup()

    def remote_files(self, mapping):
        """mapping: {(sha, path): bytes}. Missing -> 404 (permanent)."""
        def fetch(url, budget, timeout=30):
            budget.charge(url, 1)
            _, _, rest = url.partition(f"{pv.RAW}/calenb2/sports-intel-spine/")
            sha, _, path = rest.partition("/")
            if (sha, path) in mapping:
                return mapping[(sha, path)], {"url": url, "attempts": 1}
            raise t.TransportError("404", category="http_permanent", url=url, attempts=1, history=[])
        return fetch

    def verify(self, **kw):
        base = dict(repo="calenb2/sports-intel-spine", branch="main", local_head="NEW", base_head="BASE",
                    committed=True, push_outcome="success", previous_meta_path=self.prev, root=self.root,
                    is_ancestor=lambda a, b: False, budget=t.Budget(8, 90))
        base.update(kw)
        return pv.verify(**base)

    def test_published_true_requires_remote_head_and_byte_identical_readback(self):
        fetch = self.remote_files({("NEW", "distillates/soccer/meta.json"): self.META,
                                   ("NEW", "distillates/soccer/team_profiles.json"): self.PROFILES})
        r = self.verify(ls_remote=lambda b: "NEW", fetch=fetch)
        self.assertIs(r["published"], True)
        self.assertEqual(r["readback"]["NEW"]["distillates/soccer/meta.json"], h(self.META))

    def test_readback_mismatch_is_unknown_not_true(self):
        fetch = self.remote_files({("NEW", "distillates/soccer/meta.json"): b"different",
                                   ("NEW", "distillates/soccer/team_profiles.json"): self.PROFILES})
        r = self.verify(ls_remote=lambda b: "NEW", fetch=fetch)
        self.assertEqual(r["published"], "unknown")
        self.assertIn("readback did not match", r["reason"])

    def test_push_failed_remote_at_base_reports_false_with_last_good_readback(self):
        fetch = self.remote_files({("BASE", "distillates/soccer/meta.json"): self.PREV_META})
        r = self.verify(ls_remote=lambda b: "BASE", push_outcome="failure", fetch=fetch)
        self.assertIs(r["published"], False)
        self.assertIs(r["last_good_verified"], True)
        self.assertIn("last-good meta read back equal", r["reason"])

    def test_push_failed_and_last_good_unreadable_is_not_claimed(self):
        fetch = self.remote_files({})
        r = self.verify(ls_remote=lambda b: "BASE", push_outcome="failure", fetch=fetch)
        self.assertIs(r["published"], False)
        self.assertIsNone(r["last_good_verified"])
        self.assertIn("NOT confirmed", r["reason"])

    def test_remote_unreadable_is_unknown(self):
        r = self.verify(ls_remote=lambda b: None, fetch=self.remote_files({}))
        self.assertEqual(r["published"], "unknown")
        self.assertIsNone(r["remote_head"])

    def test_remote_moved_past_us_with_ancestor_check(self):
        fetch = self.remote_files({("NEW", "distillates/soccer/meta.json"): self.META,
                                   ("NEW", "distillates/soccer/team_profiles.json"): self.PROFILES})
        r = self.verify(ls_remote=lambda b: "OTHER", is_ancestor=lambda a, b: True, fetch=fetch)
        self.assertIs(r["published"], True)
        r = self.verify(ls_remote=lambda b: "OTHER", is_ancestor=lambda a, b: None, fetch=fetch)
        self.assertEqual(r["published"], "unknown")
        self.assertIn("ancestor", r["reason"])

    def test_nothing_committed_is_unchanged_with_last_good_check(self):
        fetch = self.remote_files({("BASE", "distillates/soccer/meta.json"): self.PREV_META})
        r = self.verify(ls_remote=lambda b: "BASE", local_head="BASE", committed=False,
                        push_outcome="success", fetch=fetch)
        self.assertEqual(r["published"], "unchanged")
        self.assertIs(r["last_good_verified"], True)

    def test_annotate_writes_into_current_run_record(self):
        with patch.dict("os.environ", {"GITHUB_RUN_ID": "9"}):
            self.out.write_text(json.dumps({"schema_version": 2, "run_id": "9", "stage": "verify",
                                            "publish_allowed": True, "state": "active"}))
            fetch = self.remote_files({("NEW", "distillates/soccer/meta.json"): self.META,
                                       ("NEW", "distillates/soccer/team_profiles.json"): self.PROFILES})
            r = self.verify(ls_remote=lambda b: "NEW", fetch=fetch)
            pv.annotate(r, self.out)
            rec = json.loads(self.out.read_text())
        self.assertIs(rec["published"], True)
        self.assertTrue(rec["publish_allowed"])
        self.assertEqual(rec["publish"]["remote_head"], "NEW")
        self.assertIn("publish", rec["stage_outcomes"])

    def test_cli_exit_code_flags_unconfirmed_success(self):
        with patch.object(pv, "git_ls_remote", lambda b, remote="origin": None), \
                patch.dict("os.environ", {"GITHUB_RUN_ID": "9"}):
            code = pv.main(["--repo", "calenb2/sports-intel-spine", "--local-head", "NEW", "--base-head", "BASE",
                            "--committed", "yes", "--push-outcome", "success",
                            "--previous-meta", str(self.prev), "--output", str(self.out)])
        self.assertEqual(code, 1)
        rec = json.loads(self.out.read_text())
        self.assertEqual(rec["published"], "unknown")
        with patch.object(pv, "git_ls_remote", lambda b, remote="origin": None), \
                patch.dict("os.environ", {"GITHUB_RUN_ID": "9"}):
            code = pv.main(["--repo", "calenb2/sports-intel-spine", "--local-head", "BASE", "--base-head", "BASE",
                            "--committed", "unknown", "--push-outcome", "skipped",
                            "--previous-meta", str(self.prev), "--output", str(self.out)])
        self.assertEqual(code, 0)
        self.assertIn("commit creation state unknown", json.loads(self.out.read_text())["publish"]["reason"])


if __name__ == "__main__":
    unittest.main()
