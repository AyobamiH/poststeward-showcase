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
    now = int(now if now is not None else datetime.now(timezone.utc).timestamp())
    period, offset = SLOTS[kind]
    slot = (now - offset) // period * period + offset
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (root / (kind + '.lock')).open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        receipt = root / (kind + '-' + str(slot) + '.json')
        if receipt.exists():
            old = json.loads(receipt.read_text())
            if old['state'] == 'passed':
                return old
            # Never re-execute an uncertain/failed slot without a separate review.
            raise RuntimeError('slot already attempted: ' + old['state'])
        def save(state):
            tmp = receipt.with_suffix('.tmp')
            with tmp.open('w') as stream:
                os.fchmod(stream.fileno(), 0o600)
                json.dump({'kind': kind, 'slot': slot, 'state': state}, stream)
                stream.write('\n')
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp, receipt)
            fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
            try: os.fsync(fd)
            finally: os.close(fd)
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
        return {'kind': kind, 'slot': slot, 'state': 'passed'}

if __name__ == '__main__':
    print(json.dumps(execute(sys.argv[1])))
