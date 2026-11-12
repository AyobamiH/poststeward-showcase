#!/usr/bin/env python3
"""Deliver a deduplicated, sanitised GitHub issue alert from the existing watchdog."""
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = "AyobamiH/poststeward-showcase"
ISSUE = 29
STATE_PATH = Path.home() / ".local/state/poststeward-showcase/schedule-watch-last.json"
MAX_AGE = dt.timedelta(minutes=10)
ALLOWED = {"missing", "failed", "pending", "unknown"}


def gh(*args):
    return subprocess.run(["gh", *args], text=True, capture_output=True, timeout=35, check=True).stdout


def prepare(state, now):
    """Validate untrusted local JSON before building a bounded public message."""
    checked = dt.datetime.fromisoformat(state["checked_at"].replace("Z", "+00:00"))
    if checked.tzinfo is None or not dt.timedelta(0) <= now - checked <= MAX_AGE:
        raise ValueError("stale watchdog result")
    status = state["state"]
    if status not in ALLOWED:
        raise ValueError("not an alertable watchdog result")
    workflow = state.get("workflow", "reconcile")
    if workflow not in {"reconcile", "catalogue"}:
        raise ValueError("invalid workflow")
    slot = state.get("slot") if status != "unknown" else None
    if slot:
        parsed = dt.datetime.fromisoformat(slot.replace("Z", "+00:00"))
        valid_slot = (parsed.hour == 7 and parsed.minute == 29) if workflow == "catalogue" else (
            parsed.minute == 17 and parsed.hour % 3 == 0)
        if parsed.tzinfo is None or not valid_slot or parsed.second != 0:
            raise ValueError("invalid slot")
        slot = parsed.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    else:
        slot = "api-unknown-" + checked.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%HZ")
    run_id = state.get("run_id")
    if run_id is not None and (not isinstance(run_id, int) or run_id < 1):
        raise ValueError("invalid run")
    run_part = f"Run: https://github.com/{REPO}/actions/runs/{run_id}" if run_id else "No confirmed run"
    independent = state.get("public_readback", {})
    readback_state = independent.get("state", "not-checked") if isinstance(independent, dict) else "unknown"
    if readback_state not in {"converged", "drift", "unknown", "not-checked"}:
        readback_state = "unknown"
    readback_line = f"Independent public release readback: **{readback_state}**."
    if readback_state in {"converged", "drift"}:
        beta, stable = independent.get("beta"), independent.get("stable")
        if not all(isinstance(v, str) and re.fullmatch(r"[0-9a-f]{40}", v)
                   for v in (beta, stable)):
            readback_state = "unknown"
            readback_line = "Independent public release readback: **unknown**."
        else:
            readback_line = (
                f"Independent public release readback: **{readback_state}** "
                f"(stable {stable[:12]}, beta {beta[:12]})."
            )
    catalogue_line = ""
    other = state.get("catalogue")
    if workflow == "reconcile" and isinstance(other, dict):
        other_state, other_slot = other.get("state"), other.get("slot")
        if isinstance(other_state, str) and other_state in {"passed", "missing", "failed", "pending"} and isinstance(other_slot, str):
            try:
                parsed_other = dt.datetime.fromisoformat(other_slot.replace("Z", "+00:00"))
                if (parsed_other.tzinfo is not None and parsed_other.hour == 7
                        and parsed_other.minute == 29 and parsed_other.second == 0):
                    catalogue_line = (
                        f"Daily catalogue scheduled-run check: **{other_state}** "
                        f"for {parsed_other.astimezone(dt.timezone.utc).strftime('%Y-%m-%dT%H:%MZ')}.\n"
                    )
            except ValueError:
                pass
    kind = "catalogue" if workflow == "catalogue" else "reconciliation"
    marker_prefix = "ps-showcase-catalogue-watch" if workflow == "catalogue" else "ps-showcase-watch"
    marker = f"<!-- {marker_prefix}:{slot}:{status} -->"
    body = (
        f"{marker}\n"
        f"PostSteward Showcase scheduled-{kind} watchdog alert.\n\n"
        f"Observed state: **{status}**. Expected slot: **{slot}**. {run_part}.\n"
        f"Checked: {checked.astimezone(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}.\n\n"
        f"{catalogue_line}"
        f"{readback_line} This does not satisfy scheduled-run acceptance.\n\n"
        "This is a read-only watchdog observation, not permission to dispatch, deploy or promote. "
        "Verify the GitHub schedule-event run and independent public readback before closing incident #29."
    )
    return marker, body


def deliver(marker, body):
    # Only comments by the authenticated repository owner can suppress delivery.
    # The read-before-write check makes an ambiguous POST recoverable on later runs.
    current_issue = gh("api", f"repos/{REPO}/issues/{ISSUE}", "--jq", ".state").strip()
    if current_issue != "open":
        raise RuntimeError("distribution incident is not open")
    prior = gh(
        "api", "--paginate",
        f"repos/{REPO}/issues/{ISSUE}/comments?per_page=100",
        "--jq", '.[] | select(.user.login == "AyobamiH") | .body',
    )
    if marker in prior:
        return "already-delivered"
    response = gh("api", "--method", "POST", f"repos/{REPO}/issues/{ISSUE}/comments", "-f", f"body={body}")
    url = json.loads(response).get("html_url")
    if not url:
        raise RuntimeError("comment has no confirmation URL")
    # Exact effect independently confirmed; do not assume a 2xx alone is full proof.
    confirmed = gh("api", "--paginate", f"repos/{REPO}/issues/{ISSUE}/comments?per_page=100",
                   "--jq", '.[] | select(.user.login == "AyobamiH") | .body')
    if marker not in confirmed:
        raise RuntimeError("posted watchdog alert not confirmed on readback")
    return url


def main():
    try:
        if sys.argv[1:] == ["--canary"]:
            date = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
            marker = f"<!-- ps-showcase-watch:delivery-canary:{date} -->"
            body = (
                f"{marker}\n"
                f"PostSteward Showcase watchdog **delivery canary only** ({date}). "
                "No missed schedule, failed reconciliation, provider effect or deployment is asserted. "
                "This confirms only the issue-comment escalation path and independent readback."
            )
        elif len(sys.argv) == 1:
            state = json.loads(STATE_PATH.read_text())
            marker, body = prepare(state, dt.datetime.now(dt.timezone.utc))
        else:
            raise ValueError("unknown command line argument")
        result = deliver(marker, body)
        print(json.dumps({"delivery": result, "marker": marker}), flush=True)
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError, RuntimeError) as error:
        print(json.dumps({"delivery": "unconfirmed", "reason": type(error).__name__}), flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
