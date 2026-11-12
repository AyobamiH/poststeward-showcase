"""Hermetic safety contracts for existing scheduled-reconciliation monitor."""
import datetime as dt
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
UTC = dt.timezone.utc


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


watch = load("watch_schedule", "watch-schedule.py")
alert = load("alert_schedule", "alert-schedule.py")


def run(created="2026-11-11T21:58:54Z", status="completed", conclusion="success", number=123):
    return {"event": "schedule", "created_at": created, "status": status,
            "conclusion": conclusion, "id": number}


class WatchTests(unittest.TestCase):
    def test_get_runs_retries_read_only_transport_failure(self):
        failed = subprocess.CalledProcessError(1, ["gh", "api"])
        response = SimpleNamespace(stdout=json.dumps({"workflow_runs": [run()]}))
        with patch.object(watch.subprocess, "run", side_effect=[failed, response]) as invoked, \
             patch.object(watch.time, "sleep") as sleeping:
            self.assertEqual(watch.get_runs(), [run()])
            self.assertEqual(invoked.call_count, 2)
            self.assertEqual(sleeping.call_args.args, (1,))
            for call in invoked.call_args_list:
                self.assertEqual(call.args[0][:2], ["gh", "api"])
                self.assertNotIn("POST", " ".join(call.args[0]))
                self.assertEqual(call.kwargs["timeout"], 20)
                self.assertTrue(call.kwargs["check"])

    def test_get_runs_bounded_timeouts_remain_failure(self):
        with patch.object(watch.subprocess, "run", side_effect=subprocess.TimeoutExpired("gh", 20)) as invoked, \
             patch.object(watch.time, "sleep") as sleeping:
            with self.assertRaises(subprocess.TimeoutExpired):
                watch.get_runs()
            self.assertEqual(invoked.call_count, 3)
            self.assertEqual([c.args[0] for c in sleeping.call_args_list], [1, 2])

    def test_get_runs_schema_failure_is_not_retried(self):
        with patch.object(watch.subprocess, "run", return_value=SimpleNamespace(stdout="{}")) as invoked, \
             patch.object(watch.time, "sleep") as sleeping:
            with self.assertRaises(KeyError):
                watch.get_runs()
            self.assertEqual(invoked.call_count, 1)
            sleeping.assert_not_called()

    def test_grace_retains_earlier_slot(self):
        actual = watch.assess(dt.datetime(2026, 11, 12, 0, 40, tzinfo=UTC), [run()])
        self.assertEqual(actual["slot"], "2026-11-11T21:17:00+00:00")
        self.assertEqual(actual["state"], "passed")

    def test_after_grace_checks_new_slot(self):
        actual = watch.assess(dt.datetime(2026, 11, 12, 1, 33, tzinfo=UTC), [run()])
        self.assertEqual(actual["slot"], "2026-11-12T00:17:00+00:00")
        self.assertEqual(actual["state"], "missing")

    def test_late_schedule_run_does_not_satisfy_expired_grace(self):
        # At 00:40 UTC the 00:17 slot is still inside grace, so the
        # watchdog checks 21:17. A 23:10 creation is 113 minutes late;
        # it cannot count as a healthy 21:17 natural cycle.
        actual = watch.assess(dt.datetime(2026, 11, 12, 0, 40, tzinfo=UTC),
                              [run(created="2026-11-11T23:10:00Z")])
        self.assertEqual(actual["state"], "missing")
        self.assertEqual(actual["slot"], "2026-11-11T21:17:00+00:00")
        self.assertIsNone(actual["run_id"])

    def test_schedule_delivery_within_grace_is_accepted(self):
        actual = watch.assess(dt.datetime(2026, 11, 12, 0, 40, tzinfo=UTC),
                              [run(created="2026-11-11T22:31:59Z")])
        self.assertEqual(actual["state"], "passed")

    def test_latest_run_failure_is_not_hidden_by_older_success(self):
        actual = watch.assess(dt.datetime(2026, 11, 12, 0, 40, tzinfo=UTC),
                              [run(), run(created="2026-11-11T22:03:00Z", conclusion="failure", number=456)])
        self.assertEqual(actual["state"], "failed")
        self.assertEqual(actual["run_id"], 456)

    def test_pending_is_not_success(self):
        actual = watch.assess(dt.datetime(2026, 11, 12, 0, 40, tzinfo=UTC),
                              [run(status="queued", conclusion=None)])
        self.assertEqual(actual["state"], "pending")

    def test_dispatch_not_accepted_as_schedule(self):
        manual = dict(run(), event="workflow_dispatch")
        self.assertEqual(watch.assess(dt.datetime(2026, 11, 12, 0, 40, tzinfo=UTC),
                                      [manual])["state"], "missing")

    def test_state_atomic_owner_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "private" / "last.json"
            watch.save_state({"state": "failed", "checked_at": "x"}, path)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(json.loads(path.read_text())["state"], "failed")
            watch.save_state({"state": "passed"}, path)
            self.assertEqual(json.loads(path.read_text())["state"], "passed")

    def test_unknown_state_fails_closed(self):
        with patch.object(watch, "get_runs", side_effect=TimeoutError), patch.object(watch, "save_state") as saved:
            self.assertEqual(watch.main(), 1)
            self.assertEqual(saved.call_args.args[0]["state"], "unknown")


class PublicFallbackTests(unittest.TestCase):
    script = Path("/fake/distribution-reconcile.mjs")
    beta = "a" * 40
    stable = "b" * 40

    def response(self, drift=False):
        return SimpleNamespace(stdout="DISTRIBUTION_RECONCILE " + json.dumps({
            "drift": drift, "beta": self.beta, "stable": self.stable}) + "\n")

    def test_readback_uses_bounded_non_mutating_existing_inspector(self):
        with patch.object(Path, "is_file", return_value=True), \
             patch.object(watch.subprocess, "run", return_value=self.response()) as invoked:
            self.assertEqual(watch.inspect_public_distribution(self.script),
                             {"state": "converged", "beta": self.beta, "stable": self.stable})
            self.assertEqual(invoked.call_args.args[0],
                             ["/usr/bin/node", str(self.script), "inspect"])
            self.assertEqual(invoked.call_args.kwargs["timeout"], 18)
            self.assertTrue(invoked.call_args.kwargs["check"])
            env = invoked.call_args.kwargs["env"]
            self.assertNotIn("GITHUB_TOKEN", env)
            self.assertNotIn("CLOUDFLARE_API_TOKEN", env)
            self.assertNotIn("GITHUB_OUTPUT", env)

    def test_real_drift_not_treated_as_converged(self):
        with patch.object(Path, "is_file", return_value=True), \
             patch.object(watch.subprocess, "run", return_value=self.response(True)):
            self.assertEqual(watch.inspect_public_distribution(self.script)["state"], "drift")

    def test_unknown_on_timeout_and_malformed_untrusted_stdout(self):
        with patch.object(Path, "is_file", return_value=True), \
             patch.object(watch.subprocess, "run",
                          side_effect=subprocess.TimeoutExpired("node", 18)):
            self.assertEqual(watch.inspect_public_distribution(self.script)["state"], "unknown")
        with patch.object(Path, "is_file", return_value=True), \
             patch.object(watch.subprocess, "run",
                          return_value=SimpleNamespace(stdout="DISTRIBUTION_RECONCILE {}\n")):
            self.assertEqual(watch.inspect_public_distribution(self.script)["state"], "unknown")

    def test_missing_pinned_inspector_does_not_launch_any_command(self):
        with patch.object(Path, "is_file", return_value=False), \
             patch.object(watch.subprocess, "run") as invoked:
            self.assertEqual(watch.inspect_public_distribution(self.script)["state"], "unknown")
            invoked.assert_not_called()

    def test_healthy_public_readback_never_masks_missing_schedule(self):
        independent = {"state": "converged", "beta": self.beta, "stable": self.stable}
        with patch.object(watch, "get_runs", return_value=[]), \
             patch.object(watch, "inspect_public_distribution", return_value=independent), \
             patch.object(watch, "save_state") as saved:
            self.assertEqual(watch.main(), 1)
            self.assertEqual(saved.call_args.args[0]["state"], "missing")
            self.assertEqual(saved.call_args.args[0]["public_readback"], independent)

    def test_passed_schedule_does_not_repeat_public_readback(self):
        with patch.object(watch, "assess", return_value={"state": "passed"}), \
             patch.object(watch, "get_runs", return_value=[]), \
             patch.object(watch, "inspect_public_distribution") as inspector, \
             patch.object(watch, "save_state"):
            self.assertEqual(watch.main(), 0)
            inspector.assert_not_called()


class AlertTests(unittest.TestCase):
    now = dt.datetime(2026, 11, 12, 0, 43, tzinfo=UTC)

    def state(self):
        return {"checked_at": "2026-11-12T00:42:00+00:00",
                "state": "failed", "slot": "2026-11-11T21:17:00+00:00",
                "run_id": 123}

    def test_marker_and_run_link(self):
        marker, body = alert.prepare(self.state(), self.now)
        self.assertEqual(marker, "<!-- ps-showcase-watch:2026-11-11T21:17Z:failed -->")
        self.assertIn("https://github.com/AyobamiH/poststeward-showcase/actions/runs/123", body)
        self.assertIn("not permission to dispatch, deploy or promote", body)

    def test_unknown_state_never_contains_exception_text(self):
        marker, body = alert.prepare({"state": "unknown", "reason": "unsafe text",
                 "checked_at": "2026-11-12T00:42:00+00:00"}, self.now)
        self.assertIn("api-unknown-2026-11-12T00Z", marker)
        self.assertNotIn("unsafe text", body)

    def test_public_readback_is_explicitly_separate_from_schedule(self):
        state = self.state()
        state["public_readback"] = {"state": "converged", "beta": "a" * 40, "stable": "b" * 40}
        _, body = alert.prepare(state, self.now)
        self.assertIn("Independent public release readback: **converged**", body)
        self.assertIn("does not satisfy scheduled-run acceptance", body)
        self.assertIn("stable bbbbbbbbbbbb", body)

    def test_malformed_readback_cannot_inject_incident_content(self):
        state = self.state()
        state["public_readback"] = {"state": "drift", "beta": "private\ntext", "stable": "b" * 40}
        _, body = alert.prepare(state, self.now)
        self.assertIn("readback: **unknown**", body)
        self.assertNotIn("private", body)
        state["public_readback"] = {"state": "malicious payload"}
        _, body = alert.prepare(state, self.now)
        self.assertNotIn("malicious payload", body)

    def test_accepted_status_is_not_alerted(self):
        state = self.state()
        state["state"] = "passed"
        with self.assertRaises(ValueError):
            alert.prepare(state, self.now)

    def test_stale_state_is_not_misreported(self):
        with self.assertRaises(ValueError):
            alert.prepare(self.state(), self.now + dt.timedelta(minutes=11))

    def test_invalid_slot_rejected(self):
        state = self.state()
        state["slot"] = "2026-11-11T20:23:00Z"
        with self.assertRaises(ValueError):
            alert.prepare(state, self.now)

    def test_bad_id_rejected(self):
        state = self.state()
        state["run_id"] = "secrets"
        with self.assertRaises(ValueError):
            alert.prepare(state, self.now)

    def test_preexisting_owner_comment_deduplicates_without_post(self):
        with patch.object(alert, "gh", side_effect=["open\n", "prior MARK\n"]) as mocked:
            self.assertEqual(alert.deliver("MARK", "body"), "already-delivered")
            self.assertEqual(mocked.call_count, 2)

    def test_actual_post_requires_readback_confirmation(self):
        with patch.object(alert, "gh", side_effect=[
            "open\n", "unrelated\n",
            json.dumps({"html_url": "https://github.com/AyobamiH/poststeward-showcase/issues/29#issuecomment-1"}),
            "body MARK\n",
        ]) as mocked:
            self.assertIn("issuecomment-1", alert.deliver("MARK", "body MARK"))
            self.assertEqual(mocked.call_count, 4)

    def test_uncertain_post_is_deduplicated_on_bounded_retry(self):
        # The first network effect is unknown; a subsequent service retry must
        # discover the original comment before attempting a second POST.
        lost_reply = subprocess.CalledProcessError(1, ["gh", "api", "POST"])
        with patch.object(alert, "gh", side_effect=[
            "open\n", "unrelated\n", lost_reply,
            "open\n", "existing comment with MARK\n",
        ]) as mocked:
            with self.assertRaises(subprocess.CalledProcessError):
                alert.deliver("MARK", "body MARK")
            self.assertEqual(alert.deliver("MARK", "body MARK"), "already-delivered")
            posts = [call for call in mocked.call_args_list if "POST" in call.args]
            self.assertEqual(len(posts), 1)

    def test_failed_readback_is_not_success(self):
        with patch.object(alert, "gh", side_effect=[
            "open\n", "unrelated\n", '{"html_url":"https://example.com/comment"}', "missing\n"
        ]):
            with self.assertRaises(RuntimeError):
                alert.deliver("MARK", "body MARK")

    def test_closed_issue_fails_closed_without_post(self):
        with patch.object(alert, "gh", side_effect=["closed\n"]) as mocked:
            with self.assertRaises(RuntimeError):
                alert.deliver("MARK", "body")
            self.assertEqual(mocked.call_count, 1)

    def test_installed_units_use_existing_watchdog_and_failure_only_delivery(self):
        watchdog = (HERE / "poststeward-showcase-schedule-watch.service").read_text()
        notifier = (HERE / "poststeward-showcase-schedule-alert.service").read_text()
        timer = (HERE / "poststeward-showcase-schedule-watch.timer").read_text()
        self.assertIn("OnFailure=poststeward-showcase-schedule-alert.service", watchdog)
        self.assertIn("alert-schedule.py", notifier)
        self.assertIn("Restart=on-failure", notifier)
        self.assertIn("RestartSec=60s", notifier)
        self.assertIn("StartLimitIntervalSec=600", notifier)
        self.assertIn("StartLimitBurst=4", notifier)
        self.assertNotIn("Restart=always", notifier)
        self.assertIn("*:42:00 UTC", timer)
        self.assertNotIn("OnSuccess=", watchdog)
        self.assertNotIn("OnCalendar", notifier)


if __name__ == "__main__":
    unittest.main()
