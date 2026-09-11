import { readFile, readdir } from "node:fs/promises";
import { extname, join, relative } from "node:path";

const root = new URL("../", import.meta.url);
const rootPath = root.pathname;
const canonicalPrefix = "https://github.com/AyobamiH/poststeward";
const publicOrigin = "https://poststeward.com";
const workerName = "poststeward-showcase";
const wranglerVersion = "4.130.0";

const required = [
  "README.md",
  "SECURITY.md",
  "package.json",
  "wrangler.jsonc",
  "wrangler.domain.jsonc",
  ".github/workflows/deploy.yml",
  "public/index.html",
  "public/404.html",
  "public/styles.css",
  "public/app.js",
  "public/evidence.json",
  "public/_headers",
  "public/robots.txt",
  "public/sitemap.xml",
  "scripts/smoke-deployment.mjs",
  "docs/ARCHITECTURE.md",
  "docs/CLOUDFLARE_DEPLOYMENT.md",
  "docs/LAUNCH_PLAN.md",
  "launch/PRODUCT_HUNT.md",
  "launch/OPENAI_SHOWCASE.md"
];

const failures = [];
const text = async (path) => readFile(join(rootPath, path), "utf8");

for (const path of required) {
  try { await text(path); } catch { failures.push(`missing required file: ${path}`); }
}

const evidence = JSON.parse(await text("public/evidence.json"));
if (evidence.schemaVersion !== 1) failures.push("evidence schemaVersion must be 1");
if (evidence.canonicalRepository !== canonicalPrefix) failures.push("canonicalRepository must be AyobamiH/poststeward");
if (!/^[0-9a-f]{40}$/.test(evidence.canonicalRevision ?? "")) failures.push("canonicalRevision must be a full git SHA");
if (!Array.isArray(evidence.facts) || evidence.facts.length < 5) failures.push("at least five evidence facts are required");
for (const fact of evidence.facts ?? []) {
  if (!fact.id || !fact.label || !fact.value || !fact.evidence) failures.push(`evidence fact is incomplete: ${fact.id ?? "unknown"}`);
  if (!["verified", "open"].includes(fact.state)) failures.push(`invalid evidence state for ${fact.id}: ${fact.state}`);
  if (!fact.evidence.startsWith(canonicalPrefix)) failures.push(`evidence must point to canonical GitHub source: ${fact.id}`);
}

const html = await text("public/index.html");
for (const marker of [
  "lang=\"en-GB\"",
  "<main id=\"main\">",
  "Simulation only",
  "Canonical repo",
  "meta name=\"viewport\"",
  `rel=\"canonical\" href=\"${publicOrigin}/\"`,
  `property=\"og:url\" content=\"${publicOrigin}/\"`
]) {
  if (!html.includes(marker)) failures.push(`HTML accessibility/boundary/domain marker missing: ${marker}`);
}

const css = await text("public/styles.css");
if (!css.includes("prefers-reduced-motion")) failures.push("reduced-motion support is required");
if (!css.includes(":focus-visible")) failures.push("visible keyboard focus styles are required");

const app = await text("public/app.js");
const fetchCalls = [...app.matchAll(/fetch\(([^)]+)/g)].map((match) => match[1].trim());
for (const argument of fetchCalls) {
  if (!argument.startsWith('"./') && !argument.startsWith("'./") && !argument.startsWith('"/') && !argument.startsWith("'/")) {
    failures.push(`showcase fetch must remain same-origin: ${argument.slice(0, 80)}`);
  }
}

const workerConfig = JSON.parse(await text("wrangler.jsonc"));
if (workerConfig.name !== workerName) failures.push("workers.dev config must keep the poststeward-showcase Worker name");
if (workerConfig.workers_dev !== true) failures.push("workers.dev config must explicitly enable workers_dev");
if (workerConfig.preview_urls !== false) failures.push("preview URLs must remain disabled");
if (workerConfig.assets?.directory !== "./public") failures.push("workers.dev config must serve ./public");
if (workerConfig.routes) failures.push("workers.dev config must not attach production routes/domains");

const domainConfig = JSON.parse(await text("wrangler.domain.jsonc"));
if (domainConfig.name !== workerName) failures.push("custom-domain config must deploy the same Worker name");
if (domainConfig.workers_dev !== false) failures.push("custom-domain config must disable workers.dev");
if (domainConfig.preview_urls !== false) failures.push("custom-domain config must disable preview URLs");
if (domainConfig.assets?.directory !== "./public") failures.push("custom-domain config must serve ./public");
const expectedDomains = ["poststeward.com", "www.poststeward.com"];
const configuredDomains = (domainConfig.routes ?? []).map((route) => route.pattern).sort();
if (JSON.stringify(configuredDomains) !== JSON.stringify([...expectedDomains].sort())) {
  failures.push(`custom-domain config must contain exactly: ${expectedDomains.join(", ")}`);
}
for (const route of domainConfig.routes ?? []) {
  if (route.custom_domain !== true) failures.push(`production hostname must be a Cloudflare Custom Domain: ${route.pattern}`);
}

const packageJson = JSON.parse(await text("package.json"));
if (packageJson.engines?.node !== ">=24") failures.push("Node engine must stay aligned with canonical PostSteward (>=24)");
for (const command of [packageJson.scripts?.deploy, packageJson.scripts?.["deploy:domain"]]) {
  if (!command?.includes(`wrangler@${wranglerVersion}`)) failures.push(`deploy commands must pin Wrangler ${wranglerVersion}`);
}

const deployWorkflow = await text(".github/workflows/deploy.yml");
for (const marker of [
  `wrangler@${wranglerVersion}`,
  "CLOUDFLARE_ACCOUNT_ID",
  "CLOUDFLARE_API_TOKEN",
  "persist-credentials: false",
  "WRANGLER_SEND_METRICS",
  "scripts/smoke-deployment.mjs"
]) {
  if (!deployWorkflow.includes(marker)) failures.push(`deployment workflow marker missing: ${marker}`);
}

const headers = await text("public/_headers");
for (const marker of ["Strict-Transport-Security", "Content-Security-Policy", "X-Frame-Options: DENY", "Permissions-Policy:"]) {
  if (!headers.includes(marker)) failures.push(`security header missing: ${marker}`);
}

const robots = await text("public/robots.txt");
if (!robots.includes(`${publicOrigin}/sitemap.xml`)) failures.push("robots.txt must advertise the canonical sitemap");
const sitemap = await text("public/sitemap.xml");
if (!sitemap.includes(`<loc>${publicOrigin}/</loc>`)) failures.push("sitemap must contain the canonical homepage");

async function walk(dir) {
  const out = [];
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory() && ![".git", "node_modules"].includes(entry.name)) out.push(...await walk(full));
    else if (entry.isFile() && [".js", ".mjs", ".html", ".json", ".md", ".yml", ".yaml", ".jsonc", ".txt", ".xml"].includes(extname(entry.name))) out.push(full);
  }
  return out;
}

const forbidden = [
  /THREADS_ACCESS_TOKEN/i,
  /LINKEDIN_ACCESS_TOKEN/i,
  /STRIPE_SECRET_KEY/i,
  /CLIENT_SECRET\s*[:=]/i,
  /Authorization\s*:\s*["'`]Bearer/i,
  /graph\.facebook\.com/i,
  /api\.threads\.net/i,
  /api\.x\.com/i,
  /api\.linkedin\.com/i
];

for (const file of await walk(rootPath)) {
  const rel = relative(rootPath, file);
  if (rel === "scripts/verify.mjs") continue;
  const content = await readFile(file, "utf8");
  for (const pattern of forbidden) {
    if (pattern.test(content)) failures.push(`forbidden product/provider authority pattern in ${rel}: ${pattern}`);
  }
}

if (failures.length) {
  console.error("Showcase verification failed:\n" + failures.map((failure) => `- ${failure}`).join("\n"));
  process.exit(1);
}

console.log(`Showcase verification passed: ${evidence.facts.length} evidence facts, canonical ${evidence.canonicalRevision.slice(0, 8)}, Worker ${workerName}, domain ${publicOrigin}.`);
