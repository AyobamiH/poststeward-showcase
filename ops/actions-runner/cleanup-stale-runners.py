#!/usr/bin/env python3
"""Bounded cleanup of expired *offline* PostSteward showcase JIT registrations.

Fail closed on API errors. Never delete online, busy, recent, or foreign runners.
"""
import argparse
import json
import subprocess
import time

REPO = 'repos/AyobamiH/poststeward-showcase/actions/runners'
PREFIX = 'poststeward-showcase-web-'

def gh(*args):
    # Only read-only API requests are retried; DELETE is never replayed after
    # an uncertain network result. A later scheduled run re-reads the runner.
    read_only = '--method' not in args
    for attempt in range(3 if read_only else 1):
        try:
            p = subprocess.run(['gh', 'api', *args], capture_output=True, text=True, timeout=25)
        except subprocess.TimeoutExpired:
            p = None
        if p is not None and p.returncode == 0:
            return p.stdout
        if attempt < 2 and read_only:
            time.sleep(attempt + 1)
    raise RuntimeError('GitHub API failed; no further deletion')

def candidates(now, runners, age):
    result = []
    for r in runners:
        name = r.get('name', '')
        if not name.startswith(PREFIX) or r.get('status') != 'offline' or r.get('busy') is not False:
            continue
        suffix = name[len(PREFIX):]
        if not suffix.isdigit():
            continue
        timestamp = int(suffix)
        if 0 < timestamp < now - age:
            result.append((timestamp, r['id'], name))
    return sorted(result)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--max-delete', type=int, default=5)
    parser.add_argument('--minimum-age-seconds', type=int, default=3600)
    args = parser.parse_args()
    if not 0 <= args.max_delete <= 10 or args.minimum_age_seconds < 3600:
        parser.error('limits: 0..10 deletions; age >= 3600 seconds')
    data = json.loads(gh(f'{REPO}?per_page=100'))
    if data['total_count'] > len(data['runners']):
        raise RuntimeError('Pagination required; refusing incomplete registry')
    found = candidates(int(time.time()), data['runners'], args.minimum_age_seconds)
    print(json.dumps({'mode': 'apply' if args.apply else 'dry-run', 'total': data['total_count'], 'eligible': len(found), 'selected': [name for _, _, name in found[:args.max_delete]]}))
    if not args.apply:
        return
    for _, runner_id, name in found[:args.max_delete]:
        # Recheck immediately before deleting; a runner that reconnects is protected.
        fresh = json.loads(gh(f'{REPO}/{runner_id}'))
        if fresh.get('name') != name or fresh.get('status') != 'offline' or fresh.get('busy') is not False:
            raise RuntimeError('Runner changed state; aborting cleanup')
        gh('--method', 'DELETE', f'{REPO}/{runner_id}')
        print('deleted stale offline registration:', name)

if __name__ == '__main__':
    main()
