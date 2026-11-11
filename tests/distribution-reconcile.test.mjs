import assert from 'node:assert/strict';
import { test } from 'node:test';
import { inspectDistribution } from '../scripts/distribution-reconcile.mjs';
const stable = '1'.repeat(40), beta = '2'.repeat(40);
const expiry = new Date(Date.now() + 86400000).toISOString();
const manifest = (channel, revision) => Buffer.from(JSON.stringify({ schema_version: 1, product: 'poststeward', channel, revision,
  runtime_tree_sha256: 'a'.repeat(64), expires_at: expiry,
  archive: `https://github.com/AyobamiH/poststeward/archive/${revision}.tar.gz` }));
function fixture({ drift = false, stableDrift = false, badInstaller = false, badHealth = false, expired = false } = {}) {
  return async url => {
    const value = String(url);
    const isStaging = value.includes('staging.');
    const isApp = value.includes('app.poststeward.com');
    const isWWW = value.includes('www.poststeward.com');
    let bytes;
    if (value.endsWith('/health')) bytes = Buffer.from(JSON.stringify({ status: 'ok', release: badHealth && isStaging ? stable : isStaging ? beta : stable }));
    else if (value.endsWith('/install.sh')) bytes = Buffer.from(badInstaller && isWWW ? '#!/bin/sh\nchanged' : '#!/usr/bin/env bash\ncanonical');
    else if (value.endsWith('/releases/stable.json')) bytes = manifest('stable', stableDrift && !isApp ? beta : stable);
    else if (value.endsWith('/releases/beta.json')) bytes = manifest('beta', isStaging || !drift ? beta : stable);
    else throw Error('unexpected URL');
    if (expired && isStaging && value.endsWith('/releases/beta.json')) {
      const data = JSON.parse(bytes.toString()); data.expires_at = '2000-01-01T00:00:00Z'; bytes = Buffer.from(JSON.stringify(data));
    }
    return new Response(bytes);
  };
}
test('no drift requires byte-identical public beta on both hosts', async () => {
  const value = await inspectDistribution({ send: fixture() });
  assert.equal(value.drift, false); assert.equal(value.stable, stable); assert.equal(value.beta, beta);
});
test('beta-only drift is detectable without advancing stable', async () => {
  const value = await inspectDistribution({ send: fixture({ drift: true }) });
  assert.equal(value.drift, true); assert.equal(value.stable, stable);
});
test('stable drift, installer drift, unhealthy staging and expired metadata fail closed', async () => {
  for (const options of [{ stableDrift: true }, { badInstaller: true }, { badHealth: true }, { expired: true }])
    await assert.rejects(inspectDistribution({ send: fixture(options) }));
});
