"""Regression checks for the daily catalogue within the existing Showcase watchdog."""
import datetime as dt
import importlib.util
import json
import subprocess
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
UTC = dt.timezone.utc


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


watch = load("catalogue_watch", "watch-schedule.py")
alert = load("catalogue_alert", "alert-schedule.py")


def event(created, workflow="live-catalogue-drift.yml", status="completed",
          conclusion="success", number=456):
    return {"event": "schedule", "path": f".github/workflows/{workflow}",
            "created_at": created, "status": status, "conclusion": conclusion,
            "id": number}


class CatalogueScheduleTests(unittest.TestCase):
    def test_one_read_only_api_query_covers_both_existing_workflows(self):
        events = [event("2026-11-12T07:34:00Z")]
        response = SimpleNamespace(stdout=json.dumps({"workflow_runs": events}))
        with patch.object(watch.subprocess, "run", return_value=response) as invoked:
            self.assertEqual(watch.get_runs(), events)
            command = invoked.call_args.args[0]
            self.assertEqual(command, ["gh", "api",
                "repos/AyobamiH/poststeward-showcase/actions/runs?event=schedule&per_page=100"])
            self.assertNotIn("dispatch", " ".join(command))
            self.assertNotIn("POST", " ".join(command))

    def test_accepts_timely_natural_catalogue_and_independent_reconcile(self):
        runs = [
            event("2026-11-12T07:42:00Z"),
            event("2026-11-12T06:30:00Z", workflow="distribution-reconcile.yml", number=900),
        ]
        now = dt.datetime(2026, 11, 12, 9, 42, tzinfo=UTC)
        self.assertEqual(watch.assess_catalogue(now, runs)["state"], "passed")
        self.assertEqual(watch.assess_catalogue(now, runs)["run_id"], 456)
        self.assertEqual(watch.assess(now, runs)["state"], "passed")
        self.assertEqual(watch.assess(now, runs)["run_id"], 900)

    def test_catalogue_dispatch_and_reconciliation_cannot_satisfy_schedule(self):
        manual = dict(event("2026-11-12T07:43:00Z"), event="workflow_dispatch")
        reconcile = event("2026-11-12T07:45:00Z", workflow="distribution-reconcile.yml")
        result = watch.assess_catalogue(dt.datetime(2026, 11, 12, 9, 42, tzinfo=UTC),
                                        [manual, reconcile])
        self.assertEqual(result["state"], "missing")
        self.assertIsNone(result["run_id"])

    def test_late_catalogue_success_still_missing(self):
        after_deadline = event("2026-11-12T09:01:00Z")
        actual = watch.assess_catalogue(dt.datetime(2026, 11, 12, 9, 42, tzinfo=UTC),
                                        [after_deadline])
        self.assertEqual(actual["state"], "missing")
        self.assertEqual(actual["slot"], "2026-11-12T07:29:00+00:00")

    def test_pending_and_failed_are_never_success(self):
        now = dt.datetime(2026, 11, 12, 9, 42, tzinfo=UTC)
        pending = watch.assess_catalogue(now, [event("2026-11-12T07:35:00Z", status="queued")])
        failed = watch.assess_catalogue(now, [event("2026-11-12T07:35:00Z", conclusion="failure")])
        self.assertEqual(pending["state"], "pending")
        self.assertEqual(failed["state"], "failed")

    def test_grace_does_not_prematurely_mark_today_missing(self):
        actual = watch.assess_catalogue(dt.datetime(2026, 11, 12, 8, 30, tzinfo=UTC), [])
        self.assertEqual(actual["slot"], "2026-11-11T07:29:00+00:00")
        self.assertEqual(actual["state"], "missing")

    def test_passed_reconcile_with_missing_catalogue_triggers_existing_alert_path(self):
        healthy = {"state": "passed", "slot": "2026-11-12T06:17:00+00:00", "run_id": 900}
        missing = {"state": "missing", "slot": "2026-11-12T07:29:00+00:00",
                   "run_id": None, "workflow": "catalogue"}
        with patch.object(watch, "get_runs", return_value=[]), \
             patch.object(watch, "assess", return_value=healthy), \
             patch.object(watch, "assess_catalogue", return_value=missing), \
             patch.object(watch, "inspect_public_distribution",
                          return_value={"state": "converged"}) as inspector, \
             patch.object(watch, "save_state") as saved:
            self.assertEqual(watch.main(), 1)
            state = saved.call_args.args[0]
            self.assertEqual(state["state"], "missing")
            self.assertEqual(state["workflow"], "catalogue")
            self.assertEqual(state["reconciliation"], healthy)
            inspector.assert_called_once()

    def test_reconcile_failure_not_overwritten_by_catalogue(self):
        reconcile = {"state": "missing", "slot": "2026-11-12T06:17:00+00:00", "run_id": None}
        catalogue = {"state": "missing", "slot": "2026-11-12T07:29:00+00:00",
                     "run_id": None, "workflow": "catalogue"}
        with patch.object(watch, "get_runs", return_value=[]), \
             patch.object(watch, "assess", return_value=reconcile), \
             patch.object(watch, "assess_catalogue", return_value=catalogue), \
             patch.object(watch, "inspect_public_distribution",
                          return_value={"state": "unknown"}), \
             patch.object(watch, "save_state") as saved:
            self.assertEqual(watch.main(), 1)
            state = saved.call_args.args[0]
            self.assertEqual(state["slot"], reconcile["slot"])
            self.assertEqual(state["catalogue"], catalogue)


class CatalogueAlertTests(unittest.TestCase):
    now = dt.datetime(2026, 11, 12, 9, 43, tzinfo=UTC)

    def state(self):
        return {"checked_at": "2026-11-12T09:42:00+00:00",
                "state": "missing", "workflow": "catalogue",
                "slot": "2026-11-12T07:29:00+00:00", "run_id": None}

    def test_distinct_deduplicated_catalogue_marker_and_classification(self):
        marker, body = alert.prepare(self.state(), self.now)
        self.assertEqual(marker, "<!-- ps-showcase-catalogue-watch:2026-11-12T07:29Z:missing -->")
        self.assertIn("scheduled-catalogue watchdog alert", body)
        self.assertIn("No confirmed run", body)
        self.assertIn("not permission to dispatch, deploy or promote", body)

    def test_rejects_invalid_catalogue_slot_and_workflow_injection(self):
        bad = self.state()
        bad["slot"] = "2026-11-12T07:17:00+00:00"
        with self.assertRaises(ValueError):
            alert.prepare(bad, self.now)
        bad = self.state()
        bad["workflow"] = "catalogue\nsecret"
        with self.assertRaises(ValueError):
            alert.prepare(bad, self.now)

    def test_reconciliation_alert_includes_sanitised_daily_catalogue_state(self):
        state = self.state()
        state.pop("workflow")
        state["slot"] = "2026-11-12T06:17:00+00:00"
        state["catalogue"] = {"state": "missing", "slot": "2026-11-12T07:29:00Z"}
        _, body = alert.prepare(state, self.now)
        self.assertIn("Daily catalogue scheduled-run check: **missing**", body)
        state["catalogue"]["slot"] = "2026-11-12T07:29:00Z\\nSECRET"
        _, body = alert.prepare(state, self.now)
        self.assertNotIn("SECRET", body)

    def test_existing_reconcile_alert_marker_unchanged(self):
        existing = self.state()
        existing.pop("workflow")
        existing["slot"] = "2026-11-12T06:17:00+00:00"
        marker, body = alert.prepare(existing, self.now)
        self.assertEqual(marker, "<!-- ps-showcase-watch:2026-11-12T06:17Z:missing -->")
        self.assertIn("scheduled-reconciliation watchdog alert", body)


if __name__ == "__main__":
    unittest.main()
