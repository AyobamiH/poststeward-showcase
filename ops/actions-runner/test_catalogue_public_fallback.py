"""Credential-free hosted catalogue fallback on the existing watchdog only."""
import datetime as dt
import importlib.util
import json
import subprocess
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SOURCE_ROOT = HERE.parents[1]
SCRIPT_BYTES = (SOURCE_ROOT / "scripts/verify-live-operation-contract.mjs").read_bytes()
CATALOGUE_BYTES = (SOURCE_ROOT / "public/catalog.json").read_bytes()


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


watch = module("catalogue_fallback_watch", "watch-schedule.py")
alert = module("catalogue_fallback_alert", "alert-schedule.py")


class HostedCatalogueFallbackTests(unittest.TestCase):
    checker = Path("/private/runner/scripts/verify-live-operation-contract.mjs")

    def passed(self):
        return SimpleNamespace(stdout=json.dumps({
            "status": "PASS",
            "contract": "PostSteward public operation catalogue",
            "operations": 50,
            "origin": "https://app.poststeward.com/help.json",
        }) + "\n")

    def test_read_only_pinned_checker_has_no_inherited_credentials(self):
        with patch.object(Path, "is_file", return_value=True), \
                patch.object(Path, "is_symlink", return_value=False), \
                patch.object(Path, "read_bytes", autospec=True,
                    side_effect=lambda p: SCRIPT_BYTES if p.suffix == ".mjs" else CATALOGUE_BYTES), \
                patch.object(watch.subprocess, "run", return_value=self.passed()) as invoked:
            self.assertEqual(watch.inspect_public_catalogue(self.checker),
                             {"state": "passed", "operations": 50})
        call = invoked.call_args
        self.assertEqual(call.args[0], ["/usr/bin/node", str(self.checker)])
        self.assertEqual(call.kwargs["timeout"], 18)
        self.assertTrue(call.kwargs["check"])
        self.assertEqual(call.kwargs["env"]["PATH"], "/usr/bin:/bin")
        self.assertEqual(set(call.kwargs["env"]), {"HOME", "PATH"})
        for field in ("GITHUB_TOKEN", "CLOUDFLARE_API_TOKEN", "POSTSTEWARD_RUNTIME_TOKEN"):
            self.assertNotIn(field, call.kwargs["env"])

    def test_missing_or_symlinked_pinned_source_never_executes(self):
        with patch.object(Path, "is_file", return_value=False), \
                patch.object(watch.subprocess, "run") as invoked:
            self.assertEqual(watch.inspect_public_catalogue(self.checker), {"state": "unknown"})
            invoked.assert_not_called()
        with patch.object(Path, "is_file", return_value=True), \
                patch.object(Path, "is_symlink", return_value=True), \
                patch.object(watch.subprocess, "run") as invoked:
            self.assertEqual(watch.inspect_public_catalogue(self.checker), {"state": "unknown"})
            invoked.assert_not_called()

    def test_unreviewed_script_or_catalogue_bytes_cannot_invoke_checker(self):
        with patch.object(Path, "is_file", return_value=True), \
                patch.object(Path, "is_symlink", return_value=False), \
                patch.object(Path, "read_bytes", return_value=b"tampered"), \
                patch.object(watch.subprocess, "run") as invoked:
            self.assertEqual(watch.inspect_public_catalogue(self.checker), {"state": "unknown"})
            invoked.assert_not_called()

    def test_failed_malformed_or_wrong_origin_remains_unknown(self):
        responses = [
            subprocess.CalledProcessError(1, ["node"]),
            subprocess.TimeoutExpired(["node"], 18),
            SimpleNamespace(stdout="not-json"),
            SimpleNamespace(stdout='{"status":"PASS","operations":50}'),
            SimpleNamespace(stdout=json.dumps({
                "status": "PASS", "operations": True,
                "contract": "PostSteward public operation catalogue",
                "origin": "https://app.poststeward.com/help.json"})),
            SimpleNamespace(stdout=json.dumps({
                "status": "PASS", "operations": 50,
                "contract": "PostSteward public operation catalogue",
                "origin": "https://attacker.example/help.json"})),
        ]
        with patch.object(Path, "is_file", return_value=True), \
                patch.object(Path, "is_symlink", return_value=False), \
                patch.object(Path, "read_bytes", autospec=True,
                    side_effect=lambda p: SCRIPT_BYTES if p.suffix == ".mjs" else CATALOGUE_BYTES):
            for response in responses:
                with self.subTest(response=str(response)[:70]), \
                        patch.object(watch.subprocess, "run",
                                     side_effect=response if isinstance(response, Exception) else None,
                                     return_value=None if isinstance(response, Exception) else response):
                    self.assertEqual(watch.inspect_public_catalogue(self.checker), {"state": "unknown"})

    def test_missed_schedules_keep_failure_even_if_live_catalogue_matches(self):
        independent = {"state": "passed", "operations": 50}
        with patch.object(watch, "get_runs", return_value=[]), \
                patch.object(watch, "inspect_public_distribution",
                             return_value={"state": "converged"}) as distribution, \
                patch.object(watch, "inspect_public_catalogue",
                             return_value=independent) as catalogue, \
                patch.object(watch, "save_state") as saved:
            self.assertEqual(watch.main(), 1)
            outcome = saved.call_args.args[0]
            self.assertEqual(outcome["state"], "missing")
            self.assertIsNone(outcome["run_id"])
            self.assertEqual(outcome["catalogue"]["state"], "missing")
            self.assertEqual(outcome["catalogue_public_readback"], independent)
            distribution.assert_called_once()
            catalogue.assert_called_once()

    def test_both_natural_schedules_pass_and_do_not_trigger_fallback(self):
        with patch.object(watch, "get_runs", return_value=[]), \
                patch.object(watch, "assess", return_value={"state": "passed"}), \
                patch.object(watch, "assess_catalogue", return_value={"state": "passed"}), \
                patch.object(watch, "inspect_public_catalogue") as catalogue, \
                patch.object(watch, "save_state"):
            self.assertEqual(watch.main(), 0)
            catalogue.assert_not_called()

    def test_catalogue_proof_is_sanitised_and_never_natural_acceptance(self):
        now = dt.datetime(2026, 11, 12, 10, 43, tzinfo=dt.timezone.utc)
        state = {
            "state": "missing", "workflow": "catalogue",
            "slot": "2026-11-12T07:29:00+00:00",
            "checked_at": "2026-11-12T10:42:00+00:00",
            "catalogue_public_readback": {"state": "passed", "operations": 50},
        }
        marker, body = alert.prepare(state, now)
        self.assertIn("ps-showcase-catalogue-watch", marker)
        self.assertIn("operation catalogue (GET-only): **passed** (50 operations)", body)
        self.assertIn("Not a natural scheduled-run receipt.\n", body)
        self.assertIn("does not satisfy scheduled-run acceptance", body)
        state["catalogue_public_readback"] = {
            "state": "passed", "operations": "50\nINJECTED"}
        _, body = alert.prepare(state, now)
        self.assertIn("operation catalogue (GET-only): **unknown**", body)
        self.assertNotIn("INJECTED", body)

    def test_nested_catalogue_escalation_keeps_sanitised_proof(self):
        now = dt.datetime(2026, 11, 12, 10, 43, tzinfo=dt.timezone.utc)
        state = {
            "state": "missing", "slot": "2026-11-12T09:17:00+00:00",
            "checked_at": "2026-11-12T10:42:00+00:00",
            "catalogue": {"state": "missing", "workflow": "catalogue",
                          "slot": "2026-11-12T07:29:00+00:00"},
            "catalogue_public_readback": {"state": "passed", "operations": 50},
        }
        alerts = alert.prepare_all(state, now)
        self.assertEqual(len(alerts), 2)
        self.assertNotEqual(alerts[0][0], alerts[1][0])
        for _, body in alerts:
            self.assertIn("operation catalogue (GET-only): **passed**", body)


if __name__ == "__main__":
    unittest.main()
