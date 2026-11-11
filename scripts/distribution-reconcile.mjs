import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';

const apex = 'https://poststeward.com';
const www = 'https://www.poststeward.com';
const staging = 'https://poststeward-staging.woeinvests.workers.dev';
const app = 'https://app.poststeward.com';
const sha = /^[0-9a-f]{40}$/;
const digest = value => createHash('sha256').update(value).digest('hex');

async function bounded(send, url, limit = 128 * 1024) {
  const response = await send(url, { redirect: 'error', signal: AbortSignal.timeout(20000), headers: { 'Cache-Control': 'no-cache' } });
  if (!response.ok) throw new Error(`Release endpoint ${new URL(url).pathname} returned HTTP ${response.status}`);
  const chunks = []; let length = 0;
  for await (const chunk of response.body) {
    length += chunk.byteLength;
    if (length > limit) throw new Error('Release endpoint exceeded bounded response size');
    chunks.push(Buffer.from(chunk));
  }
  return Buffer.concat(chunks);
}

function validateManifest(bytes, channel) {
  const value = JSON.parse(bytes.toString('utf8'));
  if (value.schema_version !== 1 || value.product !== 'poststeward' || value.channel !== channel ||
      !sha.test(value.revision) || !/^[0-9a-f]{64}$/.test(value.runtime_tree_sha256) ||
      value.archive !== `https://github.com/AyobamiH/poststeward/archive/${value.revision}.tar.gz` ||
      !Number.isFinite(Date.parse(value.expires_at)) || Date.parse(value.expires_at) <= Date.now())
    throw new Error(`Invalid or expired ${channel} manifest`);
  return value;
}

export async function inspectDistribution({ send = fetch } = {}) {
  const [sourceBeta, publicBeta, wwwBeta, sourceStable, publicStable, wwwStable, appInstaller, stagingInstaller, publicInstaller, wwwInstaller, appHealth, stagingHealth] = await Promise.all([
    bounded(send, `${staging}/releases/beta.json`), bounded(send, `${apex}/releases/beta.json`), bounded(send, `${www}/releases/beta.json`),
    bounded(send, `${app}/releases/stable.json`), bounded(send, `${apex}/releases/stable.json`), bounded(send, `${www}/releases/stable.json`),
    bounded(send, `${app}/install.sh`), bounded(send, `${staging}/install.sh`), bounded(send, `${apex}/install.sh`), bounded(send, `${www}/install.sh`),
    bounded(send, `${app}/health`), bounded(send, `${staging}/health`)
  ]);
  const beta = validateManifest(sourceBeta, 'beta');
  const stable = validateManifest(sourceStable, 'stable');
  // Refuse reconciliation if any stable channel or canonical installer is inconsistent.
  if (!publicStable.equals(sourceStable) || !wwwStable.equals(sourceStable)) throw new Error('Stable distribution drift: automatic beta promotion prohibited');
  if (!appInstaller.equals(stagingInstaller) || !appInstaller.equals(publicInstaller) || !appInstaller.equals(wwwInstaller))
    throw new Error('Installer drift: automatic promotion prohibited');
  if (!appInstaller.toString('utf8').startsWith('#!/usr/bin/env bash\n')) throw new Error('Installer is not canonical bash');
  const production = JSON.parse(appHealth.toString('utf8'));
  const preview = JSON.parse(stagingHealth.toString('utf8'));
  if (production.status !== 'ok' || production.release !== stable.revision || preview.status !== 'ok' || preview.release !== beta.revision)
    throw new Error('Release manifests do not match healthy application deployments');
  if (publicBeta.equals(sourceBeta) && wwwBeta.equals(sourceBeta)) return { drift: false, beta: beta.revision, stable: stable.revision, betaDigest: digest(sourceBeta) };
  // The existing public manifest may be stale, but must still be valid metadata.
  validateManifest(publicBeta, 'beta');
  validateManifest(wwwBeta, 'beta');
  return { drift: true, beta: beta.revision, stable: stable.revision, betaDigest: digest(sourceBeta) };
}

async function run(command, args, env) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { env, stdio: ['ignore', 'pipe', 'pipe'] });
    let stdout = '', stderr = '';
    const timer = setTimeout(() => child.kill('SIGKILL'), 420000);
    child.stdout.on('data', chunk => { stdout += chunk.toString(); if (stdout.length > 1048576) child.kill('SIGKILL'); });
    child.stderr.on('data', chunk => { stderr += chunk.toString(); if (stderr.length > 1048576) child.kill('SIGKILL'); });
    child.on('error', reject);
    child.on('close', code => { clearTimeout(timer); code === 0 ? resolve({ stdout, stderr }) : reject(new Error(`Isolated installer failed (${code}): ${stderr.slice(-1200)} ${stdout.slice(-1200)}`)); });
  });
}

export async function verifyBetaInstall({ installerUrl = `${apex}/install.sh`, expectedRevision, expectedTree, execute = run } = {}) {
  if (!sha.test(expectedRevision) || !/^[0-9a-f]{64}$/.test(expectedTree)) throw new Error('Expected immutable release identity required');
  const root = await mkdtemp(join(tmpdir(), 'poststeward-beta-reconcile-'));
  try {
    const env = { ...process.env, HOME: root, XDG_CONFIG_HOME: join(root, 'xdg-config'), XDG_STATE_HOME: join(root, 'xdg-state'),
      XDG_DATA_HOME: join(root, 'xdg-data'), POSTSTEWARD_RUNTIME_CONFIG_DIR: join(root, 'config'),
      POSTSTEWARD_RUNTIME_STATE_DIR: join(root, 'state'), POSTSTEWARD_SETUP_STATE_DIR: join(root, 'setup'),
      POSTSTEWARD_RELEASES_DIR: join(root, 'releases'), POSTSTEWARD_DISTRIBUTION_ORIGIN: staging };
    const script = join(root, 'install.sh');
    const { writeFile } = await import('node:fs/promises');
    await writeFile(script, await bounded(fetch, installerUrl, 64 * 1024), { mode: 0o700 });
    await execute('bash', [script, '--beta', '--prefix', join(root, 'product'), '--bin-dir', join(root, 'bin'), '--no-onboard'], env);
    const receipt = JSON.parse(await readFile(join(root, 'xdg-state', 'poststeward', 'install.json'), 'utf8'));
    if (receipt.resolved_revision !== expectedRevision || receipt.runtime_tree_sha256 !== expectedTree)
      throw new Error('Installed release receipt does not match staged beta');
    const binary = join(root, 'bin', 'poststeward');
    const version = await execute(binary, ['--version'], env);
    const help = await execute(binary, ['help', '--json'], env);
    if (!version.stdout.includes('poststeward') || !JSON.parse(help.stdout).schema_version)
      throw new Error('Installed runtime failed version/help acceptance');
    return { revision: receipt.resolved_revision, runtimeTree: receipt.runtime_tree_sha256 };
  } finally { await rm(root, { recursive: true, force: true }); }
}

if (process.argv[1] && import.meta.url === new URL(`file://${process.argv[1]}`).href) {
  const mode = process.argv[2] || 'inspect';
  const result = await inspectDistribution();
  if (mode === 'confirm' && result.drift) throw new Error('Public beta still differs from staging');
  if (mode === 'verify' && result.drift) {
    const manifest = validateManifest(await bounded(fetch, `${staging}/releases/beta.json`), 'beta');
    await verifyBetaInstall({ expectedRevision: manifest.revision, expectedTree: manifest.runtime_tree_sha256 });
  }
  console.log('DISTRIBUTION_RECONCILE ' + JSON.stringify(result));
  if (process.env.GITHUB_OUTPUT) {
    const { appendFile } = await import('node:fs/promises');
    await appendFile(process.env.GITHUB_OUTPUT, `drift=${result.drift}\nstable=${result.stable}\nbeta=${result.beta}\n`);
  }
}
