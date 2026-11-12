#!/usr/bin/env python3
"""Read-only scheduled reconciliation watchdog; fails closed, never dispatches releases."""
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = "AyobamiH/poststeward-showcase"
WORKFLOW = "distribution-reconcile.yml"
GRACE = dt.timedelta(minutes=75)
STATE_PATH = Path.home() / ".local/state/poststeward-showcase/schedule-watch-last.json"


def get_runs():
    result = subprocess.run(
        ["gh", "api", f"repos/{REPO}/actions/workflows/{WORKFLOW}/runs?event=schedule&per_page=30"],
        capture_output=True, text=True, timeout=35, check=True,
    )
    return json.loads(result.stdout)["workflow_runs"]


def assess(now, runs):
    slot = now.replace(minute=17, second=0, microsecond=0)
    slot -= dt.timedelta(hours=slot.hour % 3)
    if slot > now - GRACE:
        slot -= dt.timedelta(hours=3)
    window_end = slot + dt.timedelta(hours=3)
    matching = [
        r for r in runs
        if r.get("event") == "schedule"
        and slot <= dt.datetime.fromisoformat(r["created_at"].replace("Z", "+00:00")) < window_end
    ]
    if not matching:
        return {"state": "missing", "slot": slot.isoformat(), "run_id": None}
    latest = max(matching, key=lambda r: r["created_at"])
    state = (
        "passed" if latest.get("status") == "completed" and latest.get("conclusion") == "success"
        else "pending" if latest.get("status") != "completed"
        else "failed"
    )
    return {
        "state": state, "slot": slot.isoformat(),
        "run_id": latest["id"], "conclusion": latest.get("conclusion"),
    }


def save_state(outcome, path=STATE_PATH):
    """Atomic, owner-private state file for systemd OnFailure delivery."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, tempname = tempfile.mkstemp(prefix=".schedule-watch-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as file:
            os.fchmod(file.fileno(), 0o600)
            json.dump(outcome, file, sort_keys=True)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(tempname, path)
    finally:
        if os.path.exists(tempname):
            os.unlink(tempname)


def main():
    now = dt.datetime.now(dt.timezone.utc)
    try:
        outcome = assess(now, get_runs())
    except Exception as error:
        outcome = {"state": "unknown", "reason": type(error).__name__}
    outcome["checked_at"] = now.isoformat()
    try:
        save_state(outcome)
    except OSError as error:
        # No success without a durable alert handoff.
        print(json.dumps({"state": "unknown", "reason": type(error).__name__}), flush=True)
        return 2
    print(json.dumps(outcome), flush=True)
    # Pending beyond 75-minute grace is not successful natural-cycle evidence.
    return 0 if outcome["state"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
