import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { test } from 'node:test';

const workflow = readFileSync(fileURLToPath(new URL('../.github/workflows/live-catalogue-drift.yml', import.meta.url)), 'utf8');

test('natural catalogue check uses the existing isolated runner and only trusted main', () => {
  assert.match(workflow, /on:\n  schedule:\n    - cron: "29 7 \* \* \*"\n  workflow_dispatch:/);
  assert.match(workflow, /github\.repository == 'AyobamiH\/poststeward-showcase'/);
  assert.match(workflow, /github\.ref == 'refs\/heads\/main'/);
  assert.match(workflow, /github\.event_name == 'schedule'/);
  assert.match(workflow, /github\.event_name == 'workflow_dispatch' && github\.actor == 'AyobamiH'/);
  assert.match(workflow, /runs-on: poststeward-showcase/);
  assert.doesNotMatch(workflow, /runs-on: ubuntu-latest/);
});
test('the scheduled catalogue job remains read-only and cannot promote or dispatch releases', () => {
  assert.match(workflow, /permissions:\n  contents: read\n/);
  assert.match(workflow, /persist-credentials: false/);
  assert.match(workflow, /run: npm run verify:live-catalogue/);
  assert.doesNotMatch(workflow, /actions: write|issues: write|secrets\.|gh workflow run/);
});
