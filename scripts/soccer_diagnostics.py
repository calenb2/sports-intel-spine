"""Stage diagnostics for the soccer refresh.

Every stage (pull, distill, verify, publish) writes the same status file on
failure so the workflow always has something to retain. A diagnostic is
evidence of what happened; it never grants permission to publish.

Usage from a shell step::

    python scripts/soccer_diagnostics.py --if-missing --stage workflow --message "..."
    python scripts/soccer_diagnostics.py --annotate --stage publish --message "..."
"""
import argparse
import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "distillates/soccer/freshness_status.json"
DEFAULT_PREVIOUS_META = ROOT / "distillates/soccer/meta.json"
SCHEMA_VERSION = 2


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def run_context():
    """GitHub Actions identifiers when present; null locally."""
    env = os.environ
    return {
        "commit": env.get("GITHUB_SHA"),
        "run_id": env.get("GITHUB_RUN_ID"),
        "run_attempt": env.get("GITHUB_RUN_ATTEMPT"),
        "workflow": env.get("GITHUB_WORKFLOW"),
        "ref": env.get("GITHUB_REF"),
        "repository": env.get("GITHUB_REPOSITORY"),
        "runner_os": env.get("RUNNER_OS"),
        "python": sys.version.split()[0],
    }


def last_good_summary(previous_meta_path):
    """Vintage of the last published distillate, or an explicit gap record."""
    try:
        meta = json.loads(Path(previous_meta_path).read_text(encoding="utf-8"))
        return {"available": True,
                "data_through": meta.get("data_through"),
                "source_data_through": meta.get("source_data_through", meta.get("data_through")),
                "rows_total": meta.get("rows_total"),
                "source_rows_total": meta.get("source_rows_total", meta.get("rows_total")),
                "as_of": meta.get("as_of")}
    except (OSError, ValueError, TypeError) as exc:
        return {"available": False, "error": f"{type(exc).__name__}: {exc}"}


def classify_exception(exc):
    """Coarse error category for triage; the message carries the detail."""
    category = getattr(exc, "category", None)
    if category:
        return f"transport:{category}"
    name = type(exc).__name__
    if name == "InvalidResponse":
        return "invalid_response"
    if isinstance(exc, json.JSONDecodeError):
        return "invalid_json"
    if isinstance(exc, ValueError):
        return "validation"
    if isinstance(exc, (KeyError, TypeError, AttributeError)):
        return "schema"
    if isinstance(exc, OSError):
        return "io"
    return f"unexpected:{name}"


def base_record(stage, today=None):
    today = today or datetime.now(timezone.utc).date()
    return {"schema_version": SCHEMA_VERSION, "stage": stage, "as_of": today.isoformat(),
            "checked_at": utc_now(), **run_context()}


def failure_record(stage, exc, *, today=None, previous_meta=DEFAULT_PREVIOUS_META,
                   started_at=None, extra=None):
    record = base_record(stage, today)
    record.update({
        "state": "blocked", "publish_allowed": False,
        "error_category": classify_exception(exc),
        "error_type": type(exc).__name__,
        "errors": [f"{stage} failed: {exc}"],
        "traceback": traceback.format_exception(type(exc), exc, exc.__traceback__)[-12:],
        "started_at": started_at, "finished_at": utc_now(),
        "last_good": last_good_summary(previous_meta),
    })
    attempts = getattr(exc, "attempts", None)
    if attempts is not None:
        record["failed_url"] = getattr(exc, "url", None)
        record["failed_url_attempts"] = attempts
    if extra:
        record.update(extra)
    return record


def write_record(record, path=DEFAULT_OUTPUT):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(record, indent=2, default=str, allow_nan=False) + "\n"
    path.write_text(text, encoding="utf-8")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(f"## Soccer {record.get('stage', 'status')}\n```json\n{text}```\n")
    return text


def emit_failure(stage, exc, path=DEFAULT_OUTPUT, **kwargs):
    """Write a failure diagnostic and echo the traceback to stderr; returns the record."""
    record = failure_record(stage, exc, **kwargs)
    try:
        print(write_record(record, path))
    except OSError as write_exc:  # the one case where a diagnostic cannot be retained
        print(f"DIAGNOSTIC WRITE FAILED: {write_exc}", file=sys.stderr)
    traceback.print_exception(type(exc), exc, exc.__traceback__, file=sys.stderr)
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--message", required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--previous-meta", type=Path, default=DEFAULT_PREVIOUS_META)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--if-missing", action="store_true",
                      help="Write a gap record only when no diagnostic exists")
    mode.add_argument("--annotate", action="store_true",
                      help="Merge a stage outcome into the existing record (or create one)")
    args = parser.parse_args(argv)
    existing = None
    if args.output.exists():
        try:
            existing = json.loads(args.output.read_text(encoding="utf-8"))
        except ValueError:
            existing = {"corrupt_previous_record": True}
    if args.if_missing:
        if existing is not None:
            print(f"Diagnostic already present at {args.output}")
            return 0
        record = base_record(args.stage)
        record.update({"state": "blocked", "publish_allowed": False,
                       "error_category": "diagnostic_gap",
                       "errors": [f"{args.stage}: {args.message}"],
                       "last_good": last_good_summary(args.previous_meta)})
        write_record(record, args.output)
        return 0
    record = existing or base_record(args.stage)
    record.setdefault("stage_outcomes", {})[args.stage] = {
        "message": args.message, "at": utc_now()}
    if args.stage == "publish":
        record["published"] = False
    write_record(record, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
