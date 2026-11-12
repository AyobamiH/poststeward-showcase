import importlib.util
import pathlib
import unittest
from unittest.mock import patch
import subprocess
import json

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

    def test_missing_container_does_not_restart(self):
        registry = json.dumps({'total_count': 0, 'runners': []})
        def fake_run(*args, **kwargs):
            if args[:2] == ('gh', 'api'):
                return registry
            if args[:2] == ('docker', 'inspect'):
                raise subprocess.CalledProcessError(1, args)
            self.fail('unexpected side effect: ' + repr(args))
        with patch.object(recover, 'run', side_effect=fake_run):
            recover.main()

    def test_disappearing_container_does_not_restart(self):
        registry = json.dumps({'total_count': 0, 'runners': []})
        state = json.dumps({'Running': True, 'StartedAt': '2020-01-01T00:00:00Z'})
        calls = [0]
        def fake_run(*args, **kwargs):
            if args[:2] == ('gh', 'api'):
                return registry
            if args[:2] == ('docker', 'inspect'):
                calls[0] += 1
                if calls[0] == 1:
                    return state
                raise subprocess.CalledProcessError(1, args)
            if args[:2] == ('docker', 'exec'):
                return 'Runner.Listener\n'
            self.fail('unexpected side effect: ' + repr(args))
        with patch.object(recover, 'run', side_effect=fake_run), patch.object(recover.time, 'sleep'):
            recover.main()
        self.assertEqual(calls[0], 2)

    def test_api_error_is_not_swallowed(self):
        with patch.object(recover, 'run', side_effect=RuntimeError('API down')):
            with self.assertRaises(RuntimeError):
                recover.main()

if __name__ == '__main__':
    unittest.main()
