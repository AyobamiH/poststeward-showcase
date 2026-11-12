"""Fail-closed dual natural-schedule alert delivery without duplicate monitors."""
import contextlib
import datetime as dt
import importlib.util
import io
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("dual_alert", HERE / "alert-schedule.py")
alert = importlib.util.module_from_spec(spec)
spec.loader.exec_module(alert)
UTC = dt.timezone.utc


def both_unhealthy(checked=None):
    checked = checked or dt.datetime.now(UTC)
    slot = checked.replace(hour=6, minute=17, second=0, microsecond=0)
    return {
        "state": "missing", "slot": slot.isoformat(), "run_id": None,
        "checked_at": checked.isoformat(),
        "public_readback": {"state": "converged", "stable": "a"*40, "beta": "b"*40},
        "catalogue": {
            "workflow": "catalogue", "state": "missing",
            "slot": checked.replace(hour=7, minute=29, second=0, microsecond=0).isoformat(),
            "run_id": None
        }
    }


class DualScheduleAlertTests(unittest.TestCase):
    def test_two_failures_create_distinct_recovery_markers(self):
        state = both_unhealthy()
        results = alert.prepare_all(state, dt.datetime.now(UTC))
        self.assertEqual(len(results), 2)
        self.assertIn("ps-showcase-watch:", results[0][0])
        self.assertIn("ps-showcase-catalogue-watch:", results[1][0])
        self.assertIn("Daily catalogue scheduled-run check: **missing**", results[0][1])
        self.assertIn("Independent public release readback: **converged**", results[1][1])
        self.assertNotEqual(results[0][0], results[1][0])

    def test_healthy_catalogue_adds_no_incident(self):
        state = both_unhealthy()
        state["catalogue"]["state"] = "passed"
        self.assertEqual(len(alert.prepare_all(state, dt.datetime.now(UTC))), 1)

    def test_primary_catalogue_no_extra_incident(self):
        state = both_unhealthy()
        state.update(state.pop("catalogue"))
        self.assertEqual(len(alert.prepare_all(state, dt.datetime.now(UTC))), 1)

    def test_invalid_nested_slot_or_owner_cannot_publish_partial_set(self):
        for mutate in (
            lambda s: s["catalogue"].update(slot="2026-11-12T07:17:00Z"),
            lambda s: s["catalogue"].update(workflow="reconcile"),
            lambda s: s["catalogue"].update(state="garbled"),
        ):
            state = both_unhealthy()
            mutate(state)
            with self.subTest(state=state["catalogue"]), self.assertRaises(ValueError):
                alert.prepare_all(state, dt.datetime.now(UTC))

    def test_ambiguous_first_write_stops_second_no_retry(self):
        state = both_unhealthy()
        with patch.object(alert, "STATE_PATH", SimpleNamespace(read_text=lambda: json.dumps(state))), \
             patch.object(alert.sys, "argv", ["alert-schedule.py"]), \
             patch.object(alert, "deliver", side_effect=RuntimeError("uncertain")) as delivery, \
             contextlib.redirect_stdout(io.StringIO()) as stream:
            self.assertEqual(alert.main(), 1)
        self.assertEqual(delivery.call_count, 1)
        self.assertIn('"delivery": "unconfirmed"', stream.getvalue())

    def test_resume_reads_back_first_marker_then_delivers_second(self):
        state = both_unhealthy()
        with patch.object(alert, "STATE_PATH", SimpleNamespace(read_text=lambda: json.dumps(state))), \
             patch.object(alert.sys, "argv", ["alert-schedule.py"]), \
             patch.object(alert, "deliver", side_effect=["already-delivered", "https://github.com/example/confirmed"]) as delivery, \
             contextlib.redirect_stdout(io.StringIO()) as stream:
            self.assertEqual(alert.main(), 0)
        output = json.loads(stream.getvalue())
        self.assertEqual(len(output["deliveries"]), 2)
        self.assertEqual(output["deliveries"][0]["delivery"], "already-delivered")
        self.assertEqual(delivery.call_count, 2)

    def test_checked_at_from_primary_prevents_nested_timestamp_spoof(self):
        state = both_unhealthy()
        state["catalogue"]["checked_at"] = "2000-01-01T00:00:00+00:00"
        self.assertEqual(len(alert.prepare_all(state, dt.datetime.now(UTC))), 2)


if __name__ == "__main__":
    unittest.main()
