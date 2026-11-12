"""Hermetic safety contracts for existing scheduled-reconciliation monitor."""
import datetime as dt
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
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
    def test_grace_retains_earlier_slot(self):
        actual = watch.assess(dt.datetime(2026, 11, 12, 0, 40, tzinfo=UTC), [run()])
        self.assertEqual(actual["slot"], "2026-11-11T21:17:00+00:00")
        self.assertEqual(actual["state"], "passed")

    def test_after_grace_checks_new_slot(self):
        actual = watch.assess(dt.datetime(2026, 11, 12, 1, 33, tzinfo=UTC), [run()])
        self.assertEqual(actual["slot"], "2026-11-12T00:17:00+00:00")
        self.assertEqual(actual["state"], "missing")

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
        self.assertIn("*:42:00 UTC", timer)
        self.assertNotIn("OnSuccess=", watchdog)
        self.assertNotIn("OnCalendar", notifier)


if __name__ == "__main__":
    unittest.main()
