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
    def test_interrupted_read_only_slot_recovers_once_with_immutable_audit(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            slot = 12*3600 + 17*60
            original = {'kind': 'distribution', 'slot': slot, 'state': 'running',
                        'checked_at': '1970-01-01T12:22:00Z', 'lag_seconds': 300,
                        'origin': clock.ORIGIN}
            (root / f'distribution-{slot}.json').write_text(json.dumps(original))
            class Result: stdout = 'DISTRIBUTION_RECONCILE {"drift":false}\n'
            with patch.object(clock.subprocess, 'run', return_value=Result()) as run:
                result = clock.execute('distribution', now=12*3600+23*60, root=root)
                self.assertEqual(result['state'], 'passed')
                audit = root / f'distribution-{slot}.interrupted.json'
                proof = json.loads(audit.read_text())
                self.assertEqual(proof['state'], 'interrupted')
                self.assertEqual(proof['original_receipt'], original)
                self.assertEqual(proof['recovery_started_at'], '1970-01-01T12:23:00Z')
                self.assertEqual(audit.stat().st_mode & 0o777, 0o600)
                self.assertEqual(clock.execute('distribution', now=12*3600+24*60, root=root), result)
                self.assertEqual(run.call_count, 1)

    def test_interrupted_recovery_does_not_repeat_after_another_crash(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            slot = 12*3600 + 17*60
            receipt = root / f'distribution-{slot}.json'
            original = {'kind': 'distribution', 'slot': slot, 'state': 'running',
                        'checked_at': '1970-01-01T12:22:00Z', 'lag_seconds': 300,
                        'origin': clock.ORIGIN}
            receipt.write_text(json.dumps(original))
            # Simulate an abrupt parent death after the immutable recovery
            # marker was made and before a final pass/fail receipt was saved.
            with patch.object(clock.subprocess, 'run', side_effect=KeyboardInterrupt) as run:
                with self.assertRaises(KeyboardInterrupt):
                    clock.execute('distribution', now=12*3600+23*60, root=root)
                with self.assertRaisesRegex(RuntimeError, 'already attempted'):
                    clock.execute('distribution', now=12*3600+24*60, root=root)
                self.assertEqual(run.call_count, 1)
                self.assertEqual(json.loads(receipt.read_text())['state'], 'running')
                self.assertTrue((root / f'distribution-{slot}.interrupted.json').exists())

    def test_interrupted_slot_recovery_denies_unverifiable_or_terminal_receipts(self):
        slot = 12*3600 + 17*60
        base = {'kind': 'distribution', 'slot': slot, 'state': 'running',
                'checked_at': '1970-01-01T12:22:00Z', 'lag_seconds': 300,
                'origin': clock.ORIGIN}
        invalid = [
            {**base, 'state': 'failed'},
            {**base, 'state': 'late'},
            {**base, 'state': 'passed', 'checked_at': 'bad'},
            {**base, 'origin': 'github_schedule'},
            {**base, 'lag_seconds': True},
            {**base, 'lag_seconds': 1300},
            {**base, 'checked_at': '1970-01-01T12:22:01Z'},
            {**base, 'extra': 'unapproved'},
            {**base, 'kind': 'catalogue'},
            {**base, 'slot': slot - 10800},
        ]
        for value in invalid:
            with self.subTest(value=value), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                receipt = root / f'distribution-{slot}.json'
                receipt.write_text(json.dumps(value))
                with patch.object(clock.subprocess, 'run') as invoked:
                    with self.assertRaises(RuntimeError):
                        clock.execute('distribution', now=12*3600+23*60, root=root)
                    invoked.assert_not_called()
                self.assertEqual(json.loads(receipt.read_text()), value)
                self.assertFalse((root / f'distribution-{slot}.interrupted.json').exists())

    def test_overdue_interrupted_slot_cannot_be_relabelled_as_timely(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            slot = 12*3600 + 17*60
            (root / f'distribution-{slot}.json').write_text(json.dumps({
                'kind': 'distribution', 'slot': slot, 'state': 'running',
                'checked_at': '1970-01-01T12:22:00Z', 'lag_seconds': 300,
                'origin': clock.ORIGIN,
            }))
            with patch.object(clock.subprocess, 'run') as invoked:
                with self.assertRaises(RuntimeError):
                    clock.execute('distribution', now=12*3600+40*60, root=root)
                invoked.assert_not_called()
                self.assertFalse((root / f'distribution-{slot}.interrupted.json').exists())

    def test_recovered_drift_remains_failed_and_never_promotes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            slot = 12*3600 + 17*60
            receipt = root / f'distribution-{slot}.json'
            receipt.write_text(json.dumps({
                'kind': 'distribution', 'slot': slot, 'state': 'running',
                'checked_at': '1970-01-01T12:22:00Z', 'lag_seconds': 300,
                'origin': clock.ORIGIN,
            }))
            class Result: stdout = 'DISTRIBUTION_RECONCILE {"drift":true}\n'
            with patch.object(clock.subprocess, 'run', return_value=Result()) as run:
                with self.assertRaises(ValueError):
                    clock.execute('distribution', now=12*3600+23*60, root=root)
                self.assertEqual(json.loads(receipt.read_text())['state'], 'failed')
                with self.assertRaises(RuntimeError):
                    clock.execute('distribution', now=12*3600+24*60, root=root)
                self.assertEqual(run.call_count, 1)
                self.assertTrue((root / f'distribution-{slot}.interrupted.json').exists())

    def test_existing_interrupted_recovery_marker_prevents_ambiguous_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            slot = 12*3600 + 17*60
            original = {'kind': 'distribution', 'slot': slot, 'state': 'running',
                        'checked_at': '1970-01-01T12:22:00Z', 'lag_seconds': 300,
                        'origin': clock.ORIGIN}
            (root / f'distribution-{slot}.json').write_text(json.dumps(original))
            marker = root / f'distribution-{slot}.interrupted.json'
            marker.write_text('existing immutable crash evidence')
            with patch.object(clock.subprocess, 'run') as invoked:
                with self.assertRaisesRegex(RuntimeError, 'already attempted'):
                    clock.execute('distribution', now=12*3600+23*60, root=root)
                invoked.assert_not_called()
                self.assertEqual(marker.read_text(), 'existing immutable crash evidence')

    def test_symlinked_receipt_rejected_before_read_only_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            slot = 12*3600 + 17*60
            external = root / 'other'
            external.write_text('untrusted')
            (root / f'distribution-{slot}.json').symlink_to(external)
            with patch.object(clock.subprocess, 'run') as invoked:
                with self.assertRaisesRegex(RuntimeError, 'symlink'):
                    clock.execute('distribution', now=12*3600+23*60, root=root)
                invoked.assert_not_called()
                self.assertEqual(external.read_text(), 'untrusted')

    def test_existing_clock_unit_restarts_only_with_bounded_rate(self):
        path = Path(__file__).with_name('poststeward-showcase-clock@.service')
        unit = path.read_text()
        self.assertIn('Type=oneshot', unit)
        self.assertIn('Restart=on-failure', unit)
        self.assertIn('RestartSec=30s', unit)
        self.assertIn('StartLimitBurst=2', unit)
        self.assertIn('StartLimitIntervalSec=180', unit)
        self.assertIn('showcase-clock.py %i', unit)
        self.assertNotIn('workflow_dispatch', unit)

    def test_catalogue_requires_actual_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            class Result:
                stdout = json.dumps({
                    'status': 'PASS', 'operations': 51,
                    'contract': clock.CATALOGUE_CONTRACT,
                    'origin': clock.CATALOGUE_ORIGIN,
                }) + '\n'
            with patch.object(clock, 'require_catalogue_assets') as assets, \
                    patch.object(clock.subprocess, 'run', return_value=Result()) as run:
                self.assertEqual(clock.execute('catalogue', now=7*3600+34*60, root=Path(folder))['state'], 'passed')
                assets.assert_called_once_with()
                self.assertEqual(set(run.call_args.kwargs['env']), {'HOME', 'PATH'})

    def test_catalogue_rejects_success_shaped_incomplete_evidence(self):
        # Previously accepted by the clock despite missing contract and origin.
        with tempfile.TemporaryDirectory() as folder:
            class Result: stdout = '{"status":"PASS"}\n'
            with patch.object(clock, 'require_catalogue_assets'), \
                    patch.object(clock.subprocess, 'run', return_value=Result()):
                with self.assertRaises(ValueError):
                    clock.execute('catalogue', now=7*3600+34*60, root=Path(folder))
            receipt = json.loads(next(Path(folder).glob('catalogue-*.json')).read_text())
            self.assertEqual(receipt['state'], 'failed')

    def test_catalogue_rejects_wrong_origin_contract_or_ambiguous_evidence(self):
        good = {'status': 'PASS', 'operations': 51,
                'contract': clock.CATALOGUE_CONTRACT, 'origin': clock.CATALOGUE_ORIGIN}
        bad = [
            {**good, 'origin': 'https://attacker.example/help.json'},
            {**good, 'contract': 'unreviewed contract'},
            {**good, 'operations': True},
            {**good, 'operations': 0},
            {**good, 'operations': 501},
            {**good, 'unexpected': 'unreviewed'},
            ['PASS'],
        ]
        outputs = [json.dumps(item) + '\n' for item in bad]
        outputs += [json.dumps(good) + '\n' + json.dumps(good) + '\n', 'not-json']
        for output in outputs:
            with self.subTest(output=output[:75]), tempfile.TemporaryDirectory() as folder:
                class Result: stdout = output
                with patch.object(clock, 'require_catalogue_assets'), \
                        patch.object(clock.subprocess, 'run', return_value=Result()) as run:
                    with self.assertRaises(ValueError):
                        clock.execute('catalogue', now=7*3600+34*60, root=Path(folder))
                run.assert_called_once()
                receipt = json.loads(next(Path(folder).glob('catalogue-*.json')).read_text())
                self.assertEqual(receipt['state'], 'failed')

    def test_catalogue_requires_exact_reviewed_checker_and_snapshot_bytes(self):
        repository = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            (base / 'scripts').mkdir()
            (base / 'public').mkdir()
            script = base / 'scripts/verify-live-operation-contract.mjs'
            snapshot = base / 'public/catalog.json'
            script.write_bytes((repository / 'scripts/verify-live-operation-contract.mjs').read_bytes())
            snapshot.write_bytes((repository / 'public/catalog.json').read_bytes())
            clock.require_catalogue_assets(base)
            script.write_bytes(b'{"status":"PASS"}')
            with self.assertRaisesRegex(ValueError, 'provenance'):
                clock.require_catalogue_assets(base)
            script.unlink()
            script.symlink_to(repository / 'scripts/verify-live-operation-contract.mjs')
            with self.assertRaisesRegex(ValueError, 'provenance'):
                clock.require_catalogue_assets(base)
            script.unlink()
            script.write_bytes((repository / 'scripts/verify-live-operation-contract.mjs').read_bytes())
            snapshot.write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError, 'provenance'):
                clock.require_catalogue_assets(base)
    def test_unreviewed_catalogue_assets_fail_before_running_a_checker(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(clock, 'require_catalogue_assets',
                              side_effect=ValueError('catalogue source provenance not verified')), \
                    patch.object(clock.subprocess, 'run') as invoked:
                with self.assertRaisesRegex(ValueError, 'provenance'):
                    clock.execute('catalogue', now=7*3600+34*60, root=Path(folder))
                invoked.assert_not_called()
            receipt = json.loads(next(Path(folder).glob('catalogue-*.json')).read_text())
            self.assertEqual(receipt['state'], 'failed')

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
