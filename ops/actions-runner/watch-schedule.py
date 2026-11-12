#!/usr/bin/env python3
"""Read-only scheduled reconciliation watchdog; fails closed, never dispatches releases."""
import datetime as dt
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = "AyobamiH/poststeward-showcase"
WORKFLOW = "distribution-reconcile.yml"
CATALOGUE_WORKFLOW = "live-catalogue-drift.yml"
GRACE = dt.timedelta(minutes=75)
STATE_PATH = Path.home() / ".local/state/poststeward-showcase/schedule-watch-last.json"
READBACK_SCRIPT = Path.home() / ".local/share/poststeward-showcase-runner/distribution-reconcile.mjs"
CATALOGUE_READBACK_SCRIPT = Path.home() / ".local/share/poststeward-showcase-runner/scripts/verify-live-operation-contract.mjs"
CATALOGUE_CHECKER_SHA256 = "ad184abc5726eae621f4f89e39c46b69d5a104f0ebfc918f008ac46720d60b22"
CATALOGUE_SNAPSHOT_SHA256 = "830672e6d957d75eb836f7ac31fc09108c8023fdb36d56524f0269b484892db8"
REVISION = re.compile(r"^[0-9a-f]{40}$")


def get_runs():
    """Retry transport-only reads without dispatching or modifying any workflow.

    Three attempts stay below systemd's default 90-second oneshot limit, even
    when each gh process reaches its own 20-second timeout. Schema errors are
    not retried and all unresolved failures remain fail-closed/unknown.
    """
    command = ["gh", "api", f"repos/{REPO}/actions/runs?event=schedule&per_page=100"]
    for attempt in range(3):
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=20, check=True,
            )
            return json.loads(result.stdout)["workflow_runs"]
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


def assess_slot(runs, slot, workflow):
    """Accept only this exact workflow's on-time natural GitHub event."""
    matching = [
        r for r in runs
        if r.get("event") == "schedule"
        and r.get("path") == f".github/workflows/{workflow}"
        and slot <= dt.datetime.fromisoformat(r["created_at"].replace("Z", "+00:00")) < slot + GRACE
    ]
    if not matching:
        return {"state": "missing", "slot": slot.isoformat(), "run_id": None}
    latest = max(matching, key=lambda r: r["created_at"])
    state = (
        "passed" if latest.get("status") == "completed" and latest.get("conclusion") == "success"
        else "pending" if latest.get("status") != "completed"
        else "failed"
    )
    return {"state": state, "slot": slot.isoformat(), "run_id": latest["id"],
            "conclusion": latest.get("conclusion")}


def assess(now, runs):
    slot = now.replace(minute=17, second=0, microsecond=0)
    slot -= dt.timedelta(hours=slot.hour % 3)
    if slot > now - GRACE:
        slot -= dt.timedelta(hours=3)
    return assess_slot(runs, slot, WORKFLOW)


def assess_catalogue(now, runs):
    """Inspect the existing daily 07:29 catalogue job after its grace window."""
    slot = now.replace(hour=7, minute=29, second=0, microsecond=0)
    if slot > now - GRACE:
        slot -= dt.timedelta(days=1)
    return {**assess_slot(runs, slot, CATALOGUE_WORKFLOW), "workflow": "catalogue"}


def inspect_public_distribution(script=READBACK_SCRIPT):
    """Bounded, unprivileged GET-only fallback; never counts as a scheduled run.

    Invoke the existing canonical JavaScript inspector, not a second release
    implementation. Its inspect mode cannot dispatch, install or promote.
    The command runs without GitHub/Cloudflare credentials or GITHUB_OUTPUT.
    """
    if not script.is_file():
        return {"state": "unknown"}
    try:
        result = subprocess.run(
            ["/usr/bin/node", str(script), "inspect"],
            capture_output=True, text=True, timeout=18, check=True,
            env={"PATH": "/usr/bin:/bin", "HOME": str(Path.home())},
        )
        lines = [line for line in result.stdout.splitlines()
                 if line.startswith("DISTRIBUTION_RECONCILE ")]
        if len(lines) != 1:
            raise ValueError("invalid inspector response")
        payload = json.loads(lines[0].removeprefix("DISTRIBUTION_RECONCILE "))
        if type(payload.get("drift")) is not bool:
            raise ValueError("invalid inspector drift flag")
        if not all(isinstance(payload.get(key), str) and REVISION.fullmatch(payload[key])
                   for key in ("beta", "stable")):
            raise ValueError("invalid inspector source identity")
        return {"state": "drift" if payload["drift"] else "converged",
                "beta": payload["beta"], "stable": payload["stable"]}
    except (subprocess.SubprocessError, OSError, ValueError, TypeError, KeyError):
        return {"state": "unknown"}


def inspect_public_catalogue(script=CATALOGUE_READBACK_SCRIPT):
    """Verify the hosted catalogue using the existing GET-only source checker.

    This is independent operational readback, never a natural GitHub run.
    The installed checker and sibling public/catalog.json are pinned together
    to the reviewed Showcase source. No owner tokens reach the subprocess.
    """
    catalogue = script.parent.parent / "public/catalog.json"
    if (not script.is_file() or script.is_symlink()
            or not catalogue.is_file() or catalogue.is_symlink()):
        return {"state": "unknown"}
    try:
        # A source/fixture mismatch cannot be silently interpreted as public
        # contract acceptance. These exact hashes are reviewed in Git.
        if (hashlib.sha256(script.read_bytes()).hexdigest() != CATALOGUE_CHECKER_SHA256
                or hashlib.sha256(catalogue.read_bytes()).hexdigest() != CATALOGUE_SNAPSHOT_SHA256):
            return {"state": "unknown"}
        result = subprocess.run(
            ["/usr/bin/node", str(script)], capture_output=True, text=True,
            timeout=18, check=True,
            env={"PATH": "/usr/bin:/bin", "HOME": str(Path.home())},
        )
        lines = result.stdout.splitlines()
        if len(lines) != 1:
            raise ValueError("unexpected catalogue checker output")
        payload = json.loads(lines[0])
        operations = payload.get("operations")
        if (payload.get("status") != "PASS"
                or payload.get("contract") != "PostSteward public operation catalogue"
                or payload.get("origin") != "https://app.poststeward.com/help.json"
                or type(operations) is not int or not 0 < operations <= 500):
            raise ValueError("invalid catalogue checker proof")
        return {"state": "passed", "operations": operations}
    except (subprocess.SubprocessError, OSError, ValueError, TypeError, KeyError):
        return {"state": "unknown"}


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
    catalogue = None
    try:
        # One GET covers both existing schedules without a new monitor,
        # workflow dispatch, deployment executor or publishing authority.
        runs = get_runs()
        reconcile = assess(now, runs)
        catalogue = assess_catalogue(now, runs)
        outcome = {**reconcile, "catalogue": catalogue}
        if reconcile["state"] == "passed" and catalogue["state"] != "passed":
            outcome = {**catalogue, "reconciliation": reconcile}
    except Exception as error:
        outcome = {"state": "unknown", "reason": type(error).__name__}
    outcome["checked_at"] = now.isoformat()
    if outcome["state"] != "passed":
        # Independent GET-only evidence never changes the natural-schedule verdict.
        # Parallel checks keep both fallbacks inside the existing 90s oneshot
        # deadline even after bounded GitHub transport retries.
        if catalogue is not None and catalogue["state"] != "passed":
            try:
                with ThreadPoolExecutor(max_workers=2) as pool:
                    distribution = pool.submit(inspect_public_distribution)
                    operations = pool.submit(inspect_public_catalogue)
                    outcome["public_readback"] = distribution.result()
                    outcome["catalogue_public_readback"] = operations.result()
            except Exception:
                # An unexpected local checker failure must not prevent the
                # original missing-run state from reaching the incident handler.
                outcome["public_readback"] = {"state": "unknown"}
                outcome["catalogue_public_readback"] = {"state": "unknown"}
        else:
            outcome["public_readback"] = inspect_public_distribution()
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
