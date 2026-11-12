#!/usr/bin/env python3
"""Fail-closed, independent, GET-only Showcase reconciliation and catalogue clock.

No GitHub dispatch, provider credentials, channel promotion, or runner lifecycle writes.
Receipts are isolated from the product's operational clock and natural GitHub runs.
"""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

# An independent local readback is not evidence that GitHub fired its cron.
# Reject overdue systemd catch-up/manual invocations as timely slot receipts.
MAX_START_LAG_SECONDS = 20 * 60
ORIGIN = 'independent_local_readback'

ROOT = Path.home() / '.local/state/poststeward-showcase/clock'
SCRIPTS = Path.home() / '.local/share/poststeward-showcase-runner'
SLOTS = {'distribution': (10800, 17 * 60), 'catalogue': (86400, 7 * 3600 + 29 * 60)}
COMMANDS = {
    'distribution': [ '/usr/bin/node', str(SCRIPTS / 'distribution-reconcile.mjs'), 'confirm'],
    'catalogue': ['/usr/bin/node', str(SCRIPTS / 'scripts/verify-live-operation-contract.mjs')],
}

def execute(kind, now=None, root=ROOT, commands=None):
    if kind not in SLOTS:
        raise ValueError('unknown monitor')
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (root / (kind + '.lock')).open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        # A live invocation must be timed AFTER acquiring the durable slot
        # lock; otherwise an old queued process could inherit a fresh stamp.
        observed = int(now if now is not None else datetime.now(timezone.utc).timestamp())
        period, offset = SLOTS[kind]
        slot = (observed - offset) // period * period + offset
        lag_seconds = observed - slot
        checked_at = datetime.fromtimestamp(observed, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        receipt = root / (kind + '-' + str(slot) + '.json')
        if receipt.exists():
            old = json.loads(receipt.read_text())
            # Historic un-timestamped successes are retained, not promoted into
            # evidence of timely execution. Never re-run an ambiguous slot.
            if isinstance(old, dict) and old.get('kind') == kind and old.get('slot') == slot and old.get('state') == 'passed' and old.get('origin') == ORIGIN:
                delay = old.get('lag_seconds')
                if (type(delay) is int and 0 <= delay <= MAX_START_LAG_SECONDS
                        and old.get('checked_at') == datetime.fromtimestamp(slot + delay, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')):
                    return old
            raise RuntimeError('slot already attempted or legacy receipt has no timely provenance')
        def save(state):
            tmp = receipt.with_suffix('.tmp')
            with tmp.open('w') as stream:
                os.fchmod(stream.fileno(), 0o600)
                json.dump({'kind': kind, 'slot': slot, 'state': state,
                           'checked_at': checked_at, 'lag_seconds': lag_seconds,
                           'origin': ORIGIN}, stream)
                stream.write('\n')
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp, receipt)
            fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
            try: os.fsync(fd)
            finally: os.close(fd)
        if lag_seconds > MAX_START_LAG_SECONDS:
            # systemd Persistent=true can wake an old slot hours late; retain
            # a distinct receipt without performing or approving an old check.
            save('late')
            raise RuntimeError('slot was not observed within the independent clock grace')
        save('running')
        command = (commands or COMMANDS)[kind]
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True,
                                    timeout=75, env={'HOME': str(Path.home()), 'PATH': '/usr/bin:/bin'})
            if kind == 'distribution':
                lines = [x for x in result.stdout.splitlines() if x.startswith('DISTRIBUTION_RECONCILE ')]
                if len(lines) != 1 or json.loads(lines[0].split(' ', 1)[1]).get('drift') is not False:
                    raise ValueError('distribution convergence not proven')
            else:
                lines = [x for x in result.stdout.splitlines() if x.startswith('{')]
                if not any(json.loads(x).get('status') == 'PASS' for x in lines):
                    raise ValueError('catalogue parity not proven')
        except Exception:
            save('failed')
            raise
        save('passed')
        return {'kind': kind, 'slot': slot, 'state': 'passed',
                'checked_at': checked_at, 'lag_seconds': lag_seconds,
                'origin': ORIGIN}

if __name__ == '__main__':
    print(json.dumps(execute(sys.argv[1])))
