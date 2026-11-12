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
                with self.assertRaises(ValueError): clock.execute('distribution', now=44000, root=Path(folder))
                with self.assertRaises(RuntimeError): clock.execute('distribution', now=44000, root=Path(folder))
                self.assertEqual(run.call_count, 1)
    def test_catalogue_requires_actual_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            class Result: stdout = '{"status":"PASS","operations":50}\n'
            with patch.object(clock.subprocess, 'run', return_value=Result()):
                self.assertEqual(clock.execute('catalogue', now=40000, root=Path(folder))['state'], 'passed')
    def test_no_unrecognised_workflows(self):
        with self.assertRaises(ValueError): clock.execute('deploy')

if __name__ == '__main__': unittest.main()
