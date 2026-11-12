#!/usr/bin/env python3
"""Bounded, source-controlled maintenance of Showcase's *offline* JIT runners.

GETs may retry transport failures. DELETE is never replayed on uncertain result;
read back the complete registry and fail closed if absence cannot be established.
This has no release/publishing/deployment authority.
"""

import argparse
import json
import subprocess
import time

REPO = 'repos/AyobamiH/poststeward-showcase/actions/runners'
PREFIX = 'poststeward-showcase-web-'
TRANSIENT = ('timed out', 'timeout', 'connection reset', 'connection refused',
             'tls handshake', 'temporary failure', 'unexpected eof',
             '502 bad gateway', '503 service unavailable', '504 gateway timeout',
             '502:', '503:', '504:')


class ApiFailure(RuntimeError):
    def __init__(self, category):
        self.category = category
        super().__init__(f'GitHub API {category}; no further deletion')


def request(method, path):
    """Run a single gh call; never include provider stderr or credentials in logs."""
    command = ['gh', 'api']
    if method != 'GET':
        command += ['--method', method]
    command += [path]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=20)
    except subprocess.TimeoutExpired as exc:
        raise ApiFailure('transport_timeout') from exc
    if result.returncode == 0:
        return result.stdout
    error = result.stderr.lower()
    if 'http 404' in error or '404 not found' in error:
        raise ApiFailure('not_found')
    if any(marker in error for marker in TRANSIENT):
        raise ApiFailure('transient_transport')
    raise ApiFailure('non_retryable_error')


def get(path):
    """Retry only read-only GET transport failures, at most three attempts."""
    for attempt in range(3):
        try:
            return json.loads(request('GET', path))
        except ApiFailure as exc:
            if exc.category not in ('transient_transport', 'transport_timeout') or attempt == 2:
                raise
            time.sleep(attempt + 1)
    raise AssertionError('unreachable')


def registry():
    data = get(f'{REPO}?per_page=100')
    if (not isinstance(data, dict) or type(data.get('total_count')) is not int
            or not isinstance(data.get('runners'), list)
            or data['total_count'] != len(data['runners'])
            or data['total_count'] > 100):
        raise RuntimeError('Incomplete or malformed GitHub runner registry; refusing cleanup')
    return data


def candidates(now, runners, age):
    found = []
    for runner in runners:
        if not isinstance(runner, dict):
            continue
        name = runner.get('name')
        runner_id = runner.get('id')
        if (not isinstance(name, str) or not name.startswith(PREFIX)
                or runner.get('status') != 'offline' or runner.get('busy') is not False
                or type(runner_id) is not int or runner_id <= 0):
            continue
        suffix = name[len(PREFIX):]
        if suffix.isdigit() and 0 < int(suffix) < now - age:
            found.append((int(suffix), runner_id, name))
    return sorted(found)


def apply_one(runner_id, name):
    """Bounded single delete with independent registry readback on uncertainty."""
    fresh = get(f'{REPO}/{runner_id}')
    if fresh.get('id') != runner_id or fresh.get('name') != name or fresh.get('status') != 'offline' or fresh.get('busy') is not False:
        raise RuntimeError('Runner state changed; refusing deletion')
    try:
        request('DELETE', f'{REPO}/{runner_id}')
        return 'delete_acknowledged'
    except ApiFailure as exc:
        # DELETE might already have taken effect. Never repeat the external effect.
        all_runners = registry()['runners']
        if any(r.get('id') == runner_id or r.get('name') == name for r in all_runners):
            raise RuntimeError('Uncertain DELETE; runner still present; no retry') from exc
        return 'absent_after_uncertain_delete'


def cleanup(now, max_delete, age, apply):
    data = registry()
    found = candidates(now, data['runners'], age)
    chosen = found[:max_delete]
    print(json.dumps({'mode': 'apply' if apply else 'dry-run',
                      'total': data['total_count'], 'eligible': len(found),
                      'selected': [name for _, _, name in chosen]}))
    if not apply:
        return
    for _, runner_id, name in chosen:
        outcome = apply_one(runner_id, name)
        print(json.dumps({'runner': name, 'result': outcome}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--max-delete', type=int, default=5)
    parser.add_argument('--minimum-age-seconds', type=int, default=3600)
    args = parser.parse_args()
    if not 0 <= args.max_delete <= 10 or args.minimum_age_seconds < 3600:
        parser.error('limits: 0..10 deletions; age >= 3600 seconds')
    cleanup(int(time.time()), args.max_delete, args.minimum_age_seconds, args.apply)


if __name__ == '__main__':
    main()
