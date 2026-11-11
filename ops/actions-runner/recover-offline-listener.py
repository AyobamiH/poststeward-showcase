#!/usr/bin/env python3
"""Recover a stuck JIT listener only when GitHub reports it offline and no worker runs.

Never restart on API failure, during active work, or in the first 10 minutes.
"""
import json
import subprocess
import time

REPO = 'repos/AyobamiH/poststeward-showcase/actions/runners?per_page=100'
PREFIX = 'poststeward-showcase-web-'
MIN_AGE = 600

def run(*cmd, timeout=25):
    # Retry read-only GitHub API calls, never restart commands or effects.
    read_only = len(cmd) >= 2 and cmd[0:2] == ('gh', 'api')
    for attempt in range(3 if read_only else 1):
        try:
            return subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, check=True).stdout
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            if not read_only or attempt == 2:
                raise
            time.sleep(attempt + 1)


def has_worker():
    # ps comm never exposes runner JIT configuration or environment.
    processes = run('docker', 'exec', 'poststeward-showcase-job', 'ps', '-eo', 'comm')
    return any('Runner.Worker' in line or 'RunnerWorker' in line for line in processes.splitlines())

def main():
    data = json.loads(run('gh', 'api', REPO))
    if data['total_count'] > len(data['runners']):
        raise RuntimeError('incomplete runner registry; no restart')
    if any(r['status'] == 'online' and r['name'].startswith(PREFIX) for r in data['runners']):
        print('online runner exists; no restart')
        return
    started = json.loads(run('docker', 'inspect', 'poststeward-showcase-job', '--format', '{{json .State}}'))['StartedAt']
    from datetime import datetime, timezone
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(started.replace('Z', '+00:00'))).total_seconds()
    if age < MIN_AGE:
        print('listener younger than 10 minutes; no restart')
        return
    if has_worker():
        print('worker executing; no restart')
        return
    time.sleep(2)
    if has_worker():
        print('worker started during check; no restart')
        return
    # Fresh GitHub readback immediately before acting.
    fresh = json.loads(run('gh', 'api', REPO))
    if fresh['total_count'] > len(fresh['runners']) or any(r['status'] == 'online' and r['name'].startswith(PREFIX) for r in fresh['runners']):
        print('online runner appeared; no restart')
        return
    print('offline idle JIT listener >10m; restarting dedicated service', flush=True)
    run('systemctl', '--user', 'restart', 'poststeward-showcase-runner.service', timeout=35)

if __name__ == '__main__':
    main()
