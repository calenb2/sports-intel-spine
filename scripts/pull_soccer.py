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


def download(name, budget=None):
    """Return (body, url) from the first branch that serves a complete file."""
    budget = budget if budget is not None else new_pull_budget()
    errors = []
    for branch in BRANCHES:
        url = f"{BASE}/{branch}/{name}"
        try:
            body, info = fetch_bytes(url, budget, timeout=60, opener=urlopen)
            print(f"Downloaded {name} from {branch} in {info['attempts']} attempt(s), {info['bytes']} bytes")
            return body, url
        except TransportError as exc:
            errors.append(f"{branch}: {exc.category}: {exc}")
            if exc.category == "budget":
                break  # no point trying the next branch with nothing left to spend
    raise ValueError(f"Cannot download {name}: {'; '.join(errors)}")


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
        diag.emit_failure("pull", exc, output or diag.DEFAULT_OUTPUT, started_at=started_at,
                          extra={"transport": budget.summary(), "source_base": BASE})
        return 1


if __name__ == "__main__":
    sys.exit(main())
