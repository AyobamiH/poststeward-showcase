import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('showcase_clock', Path(__file__).with_name('showcase-clock.py'))
clock = importlib.util.module_from_spec(spec)
spec.loader.exec_module(clock)

class ClockTests(unittest.TestCase):
    def test_distribution_slot_is_durable_and_not_repeated(self):
        with tempfile.TemporaryDirectory() as folder:
            class Result: stdout = 'DISTRIBUTION_RECONCILE {"drift":false}\n'
            with patch.object(clock.subprocess, 'run', return_value=Result()) as run:
                a = clock.execute('distribution', now=12*3600+23*60, root=Path(folder))
                b = clock.execute('distribution', now=12*3600+59*60, root=Path(folder))
                self.assertEqual(a, b)
                self.assertEqual(run.call_count, 1)
                self.assertEqual(a['slot'], 12*3600+17*60)
    def test_failed_slot_cannot_be_retried(self):
        with tempfile.TemporaryDirectory() as folder:
            class Result: stdout = 'DISTRIBUTION_RECONCILE {"drift":true}\n'
            with patch.object(clock.subprocess, 'run', return_value=Result()) as run:
                with self.assertRaises(ValueError): clock.execute('distribution', now=12*3600+23*60, root=Path(folder))
                with self.assertRaises(RuntimeError): clock.execute('distribution', now=12*3600+23*60, root=Path(folder))
                self.assertEqual(run.call_count, 1)
    def test_catalogue_requires_actual_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            class Result: stdout = '{"status":"PASS","operations":50}\n'
            with patch.object(clock.subprocess, 'run', return_value=Result()):
                self.assertEqual(clock.execute('catalogue', now=7*3600+34*60, root=Path(folder))['state'], 'passed')
    def test_late_catchup_cannot_approve_old_distribution_or_catalogue(self):
        with tempfile.TemporaryDirectory() as folder:
            for kind, now in (('distribution', 12*3600+51*60),
                              ('catalogue', 13*3600+8*60)):
                with self.subTest(kind=kind):
                    class Result: stdout = 'DISTRIBUTION_RECONCILE {"drift":false}\n'
                    with patch.object(clock.subprocess, 'run', return_value=Result()) as run:
                        with self.assertRaisesRegex(RuntimeError, 'not observed within'):
                            clock.execute(kind, now=now, root=Path(folder))
                        run.assert_not_called()
                    receipt = next(Path(folder).glob(kind + '-*.json'))
                    observed = json.loads(receipt.read_text())
                    self.assertEqual(observed['state'], 'late')
                    self.assertEqual(observed['origin'], 'independent_local_readback')
                    self.assertGreater(observed['lag_seconds'], clock.MAX_START_LAG_SECONDS)
                    with patch.object(clock.subprocess, 'run') as run:
                        with self.assertRaisesRegex(RuntimeError, 'already attempted'):
                            clock.execute(kind, now=now, root=Path(folder))
                        run.assert_not_called()

    def test_on_time_receipt_contains_separate_independent_provenance(self):
        with tempfile.TemporaryDirectory() as folder:
            class Result: stdout = 'DISTRIBUTION_RECONCILE {"drift":false}\n'
            with patch.object(clock.subprocess, 'run', return_value=Result()) as run:
                receipt = clock.execute('distribution', now=12*3600+22*60, root=Path(folder))
                self.assertEqual(receipt['state'], 'passed')
                self.assertEqual(receipt['lag_seconds'], 5*60)
                self.assertEqual(receipt['checked_at'], '1970-01-01T12:22:00Z')
                self.assertEqual(receipt['origin'], 'independent_local_readback')
                self.assertEqual(clock.execute('distribution', now=12*3600+27*60,
                                               root=Path(folder)), receipt)
                self.assertEqual(run.call_count, 1)

    def test_legacy_success_without_observation_time_is_not_reaccepted(self):
        with tempfile.TemporaryDirectory() as folder:
            slot = 12*3600+17*60
            path = Path(folder) / ('distribution-' + str(slot) + '.json')
            path.write_text(json.dumps({'kind': 'distribution', 'slot': slot,
                                        'state': 'passed'}))
            with patch.object(clock.subprocess, 'run') as run:
                with self.assertRaisesRegex(RuntimeError, 'legacy receipt'):
                    clock.execute('distribution', now=12*3600+22*60, root=Path(folder))
                run.assert_not_called()
            self.assertEqual(json.loads(path.read_text())['state'], 'passed')
            self.assertNotIn('origin', json.loads(path.read_text()))

    def test_no_unrecognised_workflows(self):
        with self.assertRaises(ValueError): clock.execute('deploy')

if __name__ == '__main__': unittest.main()
