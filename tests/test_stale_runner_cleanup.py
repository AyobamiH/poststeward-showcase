"""Hermetic safety regressions: never operate on actual GitHub registrations."""
import importlib.util
import json
import pathlib
import subprocess
import unittest
from unittest.mock import patch

source = pathlib.Path(__file__).resolve().parents[1] / 'ops/cleanup-stale-runners.py'
spec = importlib.util.spec_from_file_location('cleanup_stale_runners', source)
cleanup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cleanup)


def response(value=None, error='', code=0):
    return subprocess.CompletedProcess([], code, json.dumps(value) if value is not None else '', error)


def runner(rid, ts=100, status='offline', busy=False, name=None):
    return {'id': rid, 'name': name or f'{cleanup.PREFIX}{ts}', 'status': status, 'busy': busy}


class CleanupSafetyTests(unittest.TestCase):
    def test_candidates_reject_online_busy_recent_and_foreign(self):
        all_runners = [runner(1), runner(2, status='online'), runner(3, busy=True), runner(4, ts=1999), runner(5, name='foreign-100'), runner(6, name=f'{cleanup.PREFIX}bad')]
        self.assertEqual([(100, 1, f'{cleanup.PREFIX}100')], cleanup.candidates(2000, all_runners, 360))

    @patch.object(cleanup.subprocess, 'run')
    def test_readonly_transient_retry_recovers(self, call):
        call.side_effect = [response(error='TLS handshake timeout', code=1), response({'ok': True})]
        with patch.object(cleanup.time, 'sleep') as sleep:
            self.assertEqual({'ok': True}, cleanup.get('resource'))
        self.assertEqual(2, call.call_count)
        sleep.assert_called_once_with(1)
        self.assertTrue(all('--method' not in c.args[0] for c in call.call_args_list))

    @patch.object(cleanup.subprocess, 'run')
    def test_readonly_transient_retry_is_bounded(self, call):
        call.return_value = response(error='connection reset', code=1)
        with patch.object(cleanup.time, 'sleep'):
            with self.assertRaisesRegex(cleanup.ApiFailure, 'transient_transport'):
                cleanup.get('resource')
        self.assertEqual(3, call.call_count)

    @patch.object(cleanup.subprocess, 'run')
    def test_nonretryable_auth_failure_is_not_retried(self, call):
        call.return_value = response(error='HTTP 403 forbidden', code=1)
        with self.assertRaisesRegex(cleanup.ApiFailure, 'non_retryable_error'):
            cleanup.get('resource')
        call.assert_called_once()

    @patch.object(cleanup.subprocess, 'run')
    def test_uncertain_delete_confirmed_absent_without_retry(self, call):
        call.side_effect = [response(runner(1)), response(error='connection reset', code=1), response({'total_count': 0, 'runners': []})]
        self.assertEqual('absent_after_uncertain_delete', cleanup.apply_one(1, f'{cleanup.PREFIX}100'))
        self.assertEqual(1, sum('--method' in args.args[0] for args in call.call_args_list))

    @patch.object(cleanup.subprocess, 'run')
    def test_uncertain_delete_present_fails_closed(self, call):
        call.side_effect = [response(runner(1)), response(error='timed out', code=1), response({'total_count': 1, 'runners': [runner(1)]})]
        with self.assertRaisesRegex(RuntimeError, 'Uncertain DELETE'):
            cleanup.apply_one(1, f'{cleanup.PREFIX}100')
        self.assertEqual(1, sum('--method' in args.args[0] for args in call.call_args_list))

    @patch.object(cleanup.subprocess, 'run')
    def test_uncertain_delete_registry_read_failure_fails_closed(self, call):
        call.side_effect = [response(runner(1)), response(error='connection reset', code=1)] + [response(error='connection reset', code=1)] * 3
        with patch.object(cleanup.time, 'sleep'):
            with self.assertRaises(cleanup.ApiFailure):
                cleanup.apply_one(1, f'{cleanup.PREFIX}100')
        self.assertEqual(1, sum('--method' in args.args[0] for args in call.call_args_list))

    @patch.object(cleanup.subprocess, 'run')
    def test_state_change_blocks_delete(self, call):
        call.return_value = response(runner(1, status='online'))
        with self.assertRaisesRegex(RuntimeError, 'state changed'):
            cleanup.apply_one(1, f'{cleanup.PREFIX}100')
        call.assert_called_once()

    @patch.object(cleanup.subprocess, 'run')
    def test_incomplete_registry_refused(self, call):
        call.return_value = response({'total_count': 101, 'runners': [runner(1)]})
        with self.assertRaisesRegex(RuntimeError, 'Incomplete'):
            cleanup.registry()
        call.assert_called_once()

    @patch.object(cleanup.subprocess, 'run')
    def test_dry_run_performs_no_mutation(self, call):
        call.return_value = response({'total_count': 1, 'runners': [runner(1)]})
        cleanup.cleanup(4000, 5, 3600, False)
        call.assert_called_once()
        self.assertTrue(all('--method' not in c.args[0] for c in call.call_args_list))


if __name__ == '__main__':
    unittest.main()
