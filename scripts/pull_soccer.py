"""Fetch required results atomically; never mistake a cached file for a good pull."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

from soccer_freshness import read_results

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://raw.githubusercontent.com/martj42/international_results"


def download(name):
    errors = []
    for branch in ("master", "main"):
        url = f"{BASE}/{branch}/{name}"
        try:
            with urlopen(url, timeout=45) as response:
                body = response.read()
            if not body:
                raise ValueError("Empty response")
            return body, url
        except (OSError, ValueError) as exc:
            errors.append(f"{branch}: {exc}")
    raise ValueError(f"Cannot download {name}: {'; '.join(errors)}")


def pull(raw):
    raw.mkdir(parents=True, exist_ok=True)
    body, url = download("results.csv")
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
        shootouts, _ = download("shootouts.csv")
        (raw / "shootouts.csv").write_bytes(shootouts)
    except ValueError as exc:
        print(f"Optional shootouts unavailable: {exc}")
    print(f"Pulled and validated results from {url}")


if __name__ == "__main__":
    try:
        pull(ROOT / "data/soccer/raw")
    except (ValueError, OSError, KeyError) as exc:
        sys.exit(str(exc))
