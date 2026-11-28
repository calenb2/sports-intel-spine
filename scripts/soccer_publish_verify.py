"""Verify what the publish step actually did, then record it in the status file.

Runs after the commit/push step whatever its outcome. It never guesses:

* ``published: true``      — the remote branch head is this run's commit (or
                             contains it) **and** the committed distillates read
                             back byte-for-byte from the immutable commit URL.
* ``published: "unchanged"`` — nothing was committed; remote head is the base we
                             started from and its meta.json reads back equal to
                             the previously published meta.
* ``published: false``     — our commit is not on the remote; the remote still
                             serves the base commit, whose meta.json reads back
                             equal to the previously published meta ("last-good
                             remains published" is then an *observation*).
* ``published: "unknown"`` — the remote head could not be read, or readback did
                             not match any expectation. Never reported as either
                             success or safe failure.

Readback uses the immutable ``raw.githubusercontent.com/<repo>/<sha>/<path>``
form through the bounded transport (small budget), so CDN caching of branch
names cannot mislead it.
"""
import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

import soccer_diagnostics as diag
from soccer_transport import Budget, TransportError, fetch_bytes

ROOT = Path(__file__).resolve().parents[1]
READBACK_FILES = ("distillates/soccer/meta.json", "distillates/soccer/team_profiles.json")
RAW = "https://raw.githubusercontent.com"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def git_ls_remote(branch, remote="origin"):
    """Return the remote branch head sha, or None if it cannot be determined."""
    try:
        out = subprocess.run(["git", "ls-remote", "--exit-code", remote, f"refs/heads/{branch}"],
                             capture_output=True, text=True, timeout=60, check=True).stdout
        return out.split()[0] if out.split() else None
    except (subprocess.SubprocessError, OSError, IndexError):
        return None


def git_is_ancestor(ancestor, descendant):
    try:
        subprocess.run(["git", "fetch", "--quiet", "--depth=50", "origin", descendant],
                       capture_output=True, text=True, timeout=120, check=False)
        return subprocess.run(["git", "merge-base", "--is-ancestor", ancestor, descendant],
                              capture_output=True, text=True, timeout=60).returncode == 0
    except (subprocess.SubprocessError, OSError):
        return None


def readback(repo, sha, paths, budget, fetch=fetch_bytes):
    """Return {path: sha256 or error string} for files at an immutable commit URL."""
    out = {}
    for path in paths:
        url = f"{RAW}/{repo}/{sha}/{path}"
        try:
            body, _ = fetch(url, budget, timeout=30)
            out[path] = sha256(body)
        except TransportError as exc:
            out[path] = f"error:{exc.category}:{exc}"[:200]
    return out


def local_hashes(root, paths):
    return {p: sha256((Path(root) / p).read_bytes()) for p in paths}


def verify(*, repo, branch, local_head, base_head, committed, push_outcome, previous_meta_path,
           root=ROOT, ls_remote=git_ls_remote, is_ancestor=git_is_ancestor, fetch=fetch_bytes,
           budget=None):
    budget = budget or Budget(max_requests=8, max_elapsed_s=90)
    result = {"push_outcome": push_outcome, "committed": committed, "local_head": local_head,
              "base_head": base_head, "remote_head": None, "published": "unknown",
              "last_good_verified": None, "readback": {}, "reason": None,
              "checked_at": diag.utc_now()}
    remote = ls_remote(branch)
    result["remote_head"] = remote
    if remote is None:
        result["reason"] = "remote head unreadable (git ls-remote failed)"
        return result

    try:
        previous_meta_hash = sha256(Path(previous_meta_path).read_bytes())
    except OSError:
        previous_meta_hash = None

    def last_good_check(sha):
        rb = readback(repo, sha, ("distillates/soccer/meta.json",), budget, fetch)
        result["readback"][sha] = rb
        value = rb.get("distillates/soccer/meta.json")
        if value is None or value.startswith("error:") or previous_meta_hash is None:
            return None
        return value == previous_meta_hash

    if not committed:
        if remote == local_head:
            result["published"] = "unchanged"
            result["last_good_verified"] = last_good_check(remote)
            result["reason"] = "no distillate changes to commit; remote head is this run's base"
        else:
            result["published"] = "unknown"
            result["last_good_verified"] = last_good_check(remote)
            result["reason"] = "nothing committed here but remote head moved during the run"
        return result

    local = local_hashes(root, READBACK_FILES)
    on_remote = remote == local_head
    if not on_remote:
        anc = is_ancestor(local_head, remote)
        on_remote = bool(anc)
        if anc is None:
            result["reason"] = "could not determine whether this commit is an ancestor of remote head"
    if on_remote:
        rb = readback(repo, local_head, READBACK_FILES, budget, fetch)
        result["readback"][local_head] = rb
        if all(rb.get(p) == local[p] for p in READBACK_FILES):
            result["published"] = True
            result["reason"] = "remote head contains this commit and distillates read back identical"
        else:
            result["published"] = "unknown"
            result["reason"] = "commit is on remote but readback did not match local distillates"
        return result

    # Our commit is not on the remote.
    if remote == base_head:
        result["published"] = False
        result["last_good_verified"] = last_good_check(remote)
        result["reason"] = ("push did not land; remote still at base commit" +
                            ("; last-good meta read back equal" if result["last_good_verified"]
                             else "; last-good readback NOT confirmed"))
    else:
        result["published"] = "unknown"
        result["last_good_verified"] = last_good_check(remote)
        result["reason"] = result["reason"] or "remote head is neither base nor this commit"
    return result


def annotate(result, output):
    record, rejection = diag.load_current_record(output)
    if record is None:
        record = diag.base_record("publish")
        if rejection:
            record["rejected_record"] = rejection
    record["publish"] = result
    record["published"] = result["published"]
    record["last_good_verified"] = result["last_good_verified"]
    record.setdefault("stage_outcomes", {})["publish"] = {
        "message": result["reason"], "at": result["checked_at"]}
    return diag.write_record(record, output)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="owner/name")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--local-head", required=True)
    parser.add_argument("--base-head", required=True)
    parser.add_argument("--committed", required=True, choices=["yes", "no", "unknown"],
                        help="Whether the publish step created a commit (from its step output)")
    parser.add_argument("--push-outcome", required=True, choices=["success", "failure", "skipped", "cancelled"])
    parser.add_argument("--previous-meta", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=diag.DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    result = verify(repo=args.repo, branch=args.branch, local_head=args.local_head,
                    base_head=args.base_head, committed=(args.committed == "yes"),
                    push_outcome=args.push_outcome, previous_meta_path=args.previous_meta)
    if args.committed == "unknown":
        result["reason"] = f"{result['reason']}; commit creation state unknown (publish step did not report)"
    print(annotate(result, args.output))
    # Reporting step: exit 0 unless the run claimed success but we cannot confirm it.
    return 1 if (args.push_outcome == "success" and result["published"] is not True
                 and result["published"] != "unchanged") else 0


if __name__ == "__main__":
    sys.exit(main())
