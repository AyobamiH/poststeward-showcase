import assert from 'node:assert/strict';
import { test } from 'node:test';
import { requireAcceptedBeta, dispatch, incident } from '../scripts/github-release-control.mjs';
const sha = 'a'.repeat(40);
function fixture(failure) {
  const calls = [];
  const get = async (path, options) => {
    calls.push({ path, options });
    if (path.includes('/pulls?')) return [{ number: 42, merged_at: '2026-11-11', merge_commit_sha: sha, head: { sha: 'b'.repeat(40) } }];
    if (path.includes('/check-runs?')) return { check_runs: ['verify', 'runtime (3.10)', 'runtime (3.12)', 'browser'].map(name => ({ name, status: 'completed', conclusion: failure === name ? 'failure' : 'success' })) };
    if (path.includes('/issues?')) return [];
    return null;
  };
  return { calls, get };
}
test('exact merged source requires every mandatory check to pass', async () => {
  const good = fixture(); assert.equal((await requireAcceptedBeta(sha, good.get)).pr, 42);
  const bad = fixture('browser'); await assert.rejects(requireAcceptedBeta(sha, bad.get), /browser/);
});
test('scheduled reconciliation cannot dispatch a release even with valid revisions', async () => {
  const { calls, get } = fixture();
  await assert.rejects(dispatch(sha, 'c'.repeat(40), get), /Automatic release dispatch is prohibited/);
  assert.deepEqual(calls, []);
});
test('incident writes an issue on failure and never claims a successful deployment', async () => {
  const { calls, get } = fixture(); await incident('alert', get);
  assert.equal(calls[1].options.method, 'POST');
  assert.match(calls[1].options.body.body, /No successful promotion confirmed/);
});
