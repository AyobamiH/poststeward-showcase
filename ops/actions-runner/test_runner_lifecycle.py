import importlib.util
import pathlib
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).parent

def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

cleanup = load('cleanup', 'cleanup-stale-runners.py')
recover = load('recover', 'recover-offline-listener.py')

class LifecycleTests(unittest.TestCase):
    def test_only_old_offline_idle_exact_prefix_is_eligible(self):
        now = 20000
        runners = [
            {'name':'poststeward-showcase-web-10000','status':'offline','busy':False,'id':1},
            {'name':'poststeward-showcase-web-10001','status':'online','busy':False,'id':2},
            {'name':'poststeward-showcase-web-10002','status':'offline','busy':True,'id':3},
            {'name':'poststeward-showcase-web-19000','status':'offline','busy':False,'id':4},
            {'name':'other-runner-10000','status':'offline','busy':False,'id':5},
            {'name':'poststeward-showcase-web-invalid','status':'offline','busy':False,'id':6},
        ]
        self.assertEqual(cleanup.candidates(now, runners, 3600), [(10000,1,'poststeward-showcase-web-10000')])

    def test_worker_detection_prevents_recovery(self):
        with patch.object(recover, 'run', return_value='Runner.Listener\nRunner.Worker\n'):
            self.assertTrue(recover.has_worker())

    def test_idle_detection(self):
        with patch.object(recover, 'run', return_value='Runner.Listener\n'):
            self.assertFalse(recover.has_worker())

    def test_api_error_is_not_swallowed(self):
        with patch.object(recover, 'run', side_effect=RuntimeError('API down')):
            with self.assertRaises(RuntimeError):
                recover.main()

if __name__ == '__main__':
    unittest.main()
