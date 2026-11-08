"""Fetch required results atomically; never mistake a cached file for a good pull.

Downloads go through the bounded transport (``soccer_transport``): truncated
bodies, timeouts and retryable HTTP statuses are retried within a budget, a
permanent error on one branch falls through to the next, and a failure writes a
``pull`` stage diagnostic so the workflow retains evidence without publishing.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

import soccer_diagnostics as diag
from soccer_freshness import read_results
from soccer_transport import Budget, TransportError, fetch_bytes

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://raw.githubusercontent.com/martj42/international_results"
BRANCHES = ("master", "main")
PULL_MAX_REQUESTS = 16     # 2 files x 2 branches x 4 attempts
PULL_MAX_ELAPSED_S = 420


def new_pull_budget():
    return Budget(max_requests=PULL_MAX_REQUESTS, max_elapsed_s=PULL_MAX_ELAPSED_S)


class DownloadError(TransportError, ValueError):
    """Every branch failed. Keeps each branch's typed transport failure.

    Subclasses ``ValueError`` so the optional-file path and older callers that
    catch ``ValueError`` still work, while ``category``/``url``/``attempts``/
    ``failures`` survive into the diagnostic instead of collapsing to
    "validation".
    """

    def __init__(self, name, failures, history):
        last = failures[-1]
        detail = "; ".join(f"{f['branch']}: {f['category']} after {f['attempts']} attempt(s): {f['error']}"
                           for f in failures)
        super().__init__(f"Cannot download {name}: {detail}", category=last["category"],
                         url=last["url"], attempts=last["attempts"], history=history,
                         last_error=last.get("exception"))
        self.name = name
        self.failures = [{k: v for k, v in f.items() if k != "exception"} for f in failures]


def download(name, budget=None):
    """Return (body, url) from the first branch that serves a complete file."""
    budget = budget if budget is not None else new_pull_budget()
    failures = []
    for branch in BRANCHES:
        url = f"{BASE}/{branch}/{name}"
        try:
            body, info = fetch_bytes(url, budget, timeout=60, opener=urlopen)
            print(f"Downloaded {name} from {branch} in {info['attempts']} attempt(s), {info['bytes']} bytes")
            return body, url
        except TransportError as exc:
            failures.append({"branch": branch, "url": exc.url, "category": exc.category,
                             "attempts": exc.attempts, "error": str(exc.last_error or exc)[:300],
                             "exception": exc})
            if exc.category == "budget":
                break  # no point trying the next branch with nothing left to spend
    raise DownloadError(name, failures, budget.history)


def pull(raw, budget=None):
    budget = budget if budget is not None else new_pull_budget()
    raw.mkdir(parents=True, exist_ok=True)
    body, url = download("results.csv", budget)
    temp = raw / "results.csv.tmp"
    try:
        temp.write_bytes(body)
        read_results(temp, datetime.now(timezone.utc).date())
        temp.replace(raw / "results.csv")
    finally:
        temp.unlink(missing_ok=True)
    manifest_path = raw / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"]["results.csv"].update({
        "source": url, "pulled_at": datetime.now(timezone.utc).isoformat(),
    })
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    # shootouts.csv is not consumed by the distiller. Preserve the previous copy
    # when unavailable; do not confuse its optional failure with results success.
    try:
        shootouts, _ = download("shootouts.csv", budget)
        (raw / "shootouts.csv").write_bytes(shootouts)
    except ValueError as exc:
        print(f"Optional shootouts unavailable: {exc}")
    print(f"Pulled and validated results from {url}")
    return budget


def main(raw=None, output=None):
    started_at = diag.utc_now()
    budget = new_pull_budget()
    try:
        pull(raw or ROOT / "data/soccer/raw", budget)
        return 0
    except Exception as exc:  # noqa: BLE001 - every pull failure leaves a diagnostic
        extra = {"transport": budget.summary(), "source_base": BASE}
        if isinstance(exc, DownloadError):
            extra["download_failures"] = exc.failures
            extra["download_file"] = exc.name
        diag.emit_failure("pull", exc, output or diag.DEFAULT_OUTPUT, started_at=started_at,
                          extra=extra)
        return 1


if __name__ == "__main__":
    sys.exit(main())
