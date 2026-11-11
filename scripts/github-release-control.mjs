// GitHub API controller; does not require gh CLI in the isolated runner image.
const owner = 'AyobamiH';
const showcase = `${owner}/poststeward-showcase`;
const source = `${owner}/poststeward`;
const incidentTitle = 'Distribution reconciliation failed';
const token = process.env.GITHUB_TOKEN;
const runUrl = `${process.env.GITHUB_SERVER_URL || 'https://github.com'}/${process.env.GITHUB_REPOSITORY || showcase}/actions/runs/${process.env.GITHUB_RUN_ID || 'unknown'}`;

export async function api(path, { method = 'GET', body, send = fetch } = {}) {
  if (!token) throw new Error('Scoped GitHub Actions token is missing');
  const response = await send(`https://api.github.com/${path}`, {
    method, redirect: 'error', signal: AbortSignal.timeout(20000),
    headers: { Authorization: ["Bearer", token].join(" "), Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'poststeward-release-controller', ...(body ? { 'Content-Type': 'application/json' } : {}) },
    ...(body ? { body: JSON.stringify(body) } : {})
  });
  if (!response.ok) throw new Error(`GitHub ${method} ${path.split('?')[0]} returned HTTP ${response.status}`);
  return response.status === 204 ? null : response.json();
}

export async function requireAcceptedBeta(revision, get = api) {
  if (!/^[0-9a-f]{40}$/.test(revision)) throw new Error('Exact staged beta revision required');
  const prs = await get(`repos/${source}/commits/${revision}/pulls?per_page=100`);
  const merged = prs.filter(pr => pr.merged_at && pr.merge_commit_sha === revision);
  if (merged.length !== 1) throw new Error('Expected exactly one merged source PR matching staged beta');
  const checks = await get(`repos/${source}/commits/${merged[0].head.sha}/check-runs?per_page=100`);
  const required = ['verify', 'runtime (3.10)', 'runtime (3.12)', 'browser'];
  for (const name of required) {
    const matches = checks.check_runs.filter(run => run.name === name);
    if (!matches.length || matches.some(run => run.status !== 'completed' || run.conclusion !== 'success'))
      throw new Error(`Staged beta source check ${name} is missing, failed or incomplete`);
  }
  return { pr: merged[0].number, revision };
}

// Scheduled reconciliation is read-only. A release must be authorised and
// dispatched separately through the protected deployment workflow.
export async function dispatch() {
  throw new Error('Automatic release dispatch is prohibited; use the protected manual deployment workflow');
}

export async function incident(mode, get = api) {
  const issues = await get(`repos/${showcase}/issues?state=open&per_page=100`);
  const existing = issues.find(issue => !issue.pull_request && issue.title === incidentTitle);
  if (mode === 'alert') {
    const message = `Automatic reconciliation failed or was blocked. No successful promotion confirmed. Investigate ${runUrl}. Stable is never promoted automatically.`;
    if (existing) await get(`repos/${showcase}/issues/${existing.number}/comments`, { method: 'POST', body: { body: message } });
    else await get(`repos/${showcase}/issues`, { method: 'POST', body: { title: incidentTitle, body: message } });
  } else if (mode === 'resolve' && existing) {
    await get(`repos/${showcase}/issues/${existing.number}/comments`, { method: 'POST', body: { body: `Recovered: both public beta hosts match staging and stable remains pinned. ${runUrl}` } });
    await get(`repos/${showcase}/issues/${existing.number}`, { method: 'PATCH', body: { state: 'closed', state_reason: 'completed' } });
  }
}

if (process.argv[1] && import.meta.url === new URL(`file://${process.argv[1]}`).href) {
  const mode = process.argv[2];
  if (mode === 'check') console.log(JSON.stringify(await requireAcceptedBeta(process.env.BETA)));
  else if (mode === 'dispatch') await dispatch(process.env.STABLE, process.env.BETA);
  else if (mode === 'alert' || mode === 'resolve') await incident(mode);
  else throw new Error('Unknown GitHub release controller operation');
}
