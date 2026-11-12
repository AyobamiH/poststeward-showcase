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
    run_part = (f"Run: https://github.com/{REPO}/actions/runs/{run_id}"
                if run_id else "No qualifying timely GitHub schedule event")
    # Out-of-window arrivals are diagnostic only: the GitHub schedule event
    # provides no authoritative intended-slot timestamp. Strictly validate
    # all fields before interpolating them into a GitHub incident comment.
    observation_line = ""
    observation = state.get("out_of_window_observation")
    if observation is not None:
        if not isinstance(observation, dict) or "slot" not in state:
            raise ValueError("invalid out-of-window observation")
        observed_id = observation.get("run_id")
        if not isinstance(observed_id, int) or isinstance(observed_id, bool) or observed_id < 1:
            raise ValueError("invalid out-of-window run")
        observed_time = dt.datetime.fromisoformat(observation["created_at"].replace("Z", "+00:00"))
        nominal_slot = dt.datetime.fromisoformat(state["slot"].replace("Z", "+00:00"))
        interval = dt.timedelta(days=1) if workflow == "catalogue" else dt.timedelta(hours=3)
        if (observed_time.tzinfo is None or nominal_slot.tzinfo is None
                or not nominal_slot + dt.timedelta(minutes=75) <= observed_time < nominal_slot + interval
                or observed_time > checked):
            raise ValueError("invalid out-of-window timestamp")
        observation_line = (
            f"Out-of-window natural event observed: https://github.com/{REPO}/actions/runs/{observed_id} "
            f"at {observed_time.astimezone(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}. "
            "GitHub does not attest which nominal slot caused this event; "
            "it is not timely acceptance evidence.\n\n"
        )
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
    catalogue_proof = state.get("catalogue_public_readback")
    catalogue_proof_line = ""
    if catalogue_proof is not None:
        valid = isinstance(catalogue_proof, dict) and catalogue_proof.get("state") == "passed"
        count = catalogue_proof.get("operations") if valid else None
        if type(count) is int and 0 < count <= 500:
            catalogue_proof_line = (
                f"Independent hosted operation catalogue (GET-only): **passed** "
                f"({count} operations). Not a natural scheduled-run receipt.\n"
            )
        else:
            catalogue_proof_line = (
                "Independent hosted operation catalogue (GET-only): **unknown**. "
                "Not a natural scheduled-run receipt.\n"
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
        f"{observation_line}"
        f"{catalogue_line}"
        f"{catalogue_proof_line}"
        f"{readback_line} This does not satisfy scheduled-run acceptance.\n\n"
        "This is a read-only watchdog observation, not permission to dispatch, deploy or promote. "
        "Verify the GitHub schedule-event run and independent public readback before closing incident #29."
    )
    return marker, body



def prepare_all(state, now):
    """Retain distinct alerts when both existing natural schedules fail.

    The watchdog's primary outcome is reconciliation if BOTH jobs are unhealthy;
    the daily catalogue is then nested in that same atomic state handoff.
    Alerting only on the primary misses the catalogue-specific incident marker.
    Validate BOTH messages before any GitHub write, preserving fail-closed
    behaviour if the owner-private state is corrupt or unexpectedly shaped.
    """
    alerts = [prepare(state, now)]
    if state.get("workflow", "reconcile") != "reconcile" or "catalogue" not in state:
        return alerts
    catalogue = state["catalogue"]
    if not isinstance(catalogue, dict) or catalogue.get("workflow") != "catalogue":
        raise ValueError("invalid nested catalogue result")
    status = catalogue.get("state")
    if status == "passed":
        return alerts
    if status not in ALLOWED:
        raise ValueError("invalid nested catalogue status")
    # Do not permit a nested JSON object to control the checked_at timestamp
    # or the independent readback text delivered under the existing alert.
    distinct = dict(catalogue)
    distinct["checked_at"] = state["checked_at"]
    distinct["public_readback"] = state.get("public_readback", {})
    distinct["catalogue_public_readback"] = state.get("catalogue_public_readback")
    alerts.append(prepare(distinct, now))
    return alerts

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
            alerts = [(marker, body)]
        elif len(sys.argv) == 1:
            state = json.loads(STATE_PATH.read_text())
            alerts = prepare_all(state, dt.datetime.now(dt.timezone.utc))
        else:
            raise ValueError("unknown command line argument")
        results = []
        for marker, body in alerts:
            # Each marker has its own remote read-before-write and readback.
            # An ambiguous POST stops this cycle without replaying the effect.
            results.append({"delivery": deliver(marker, body), "marker": marker})
        output = results[0] if len(results) == 1 else {"deliveries": results}
        print(json.dumps(output), flush=True)
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError, RuntimeError) as error:
        print(json.dumps({"delivery": "unconfirmed", "reason": type(error).__name__}), flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
