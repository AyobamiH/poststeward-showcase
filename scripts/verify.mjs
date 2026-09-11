import { readFile, readdir } from "node:fs/promises";
import { extname, join, relative } from "node:path";

const root = new URL("../", import.meta.url);
const rootPath = root.pathname;
const publicOrigin = "https://poststeward.com";
const workerName = "poststeward-showcase";
const wranglerVersion = "4.130.0";
const cloudflareAccountId = "6ddcbcb8474f1a7e460b2f0aabec0e2f";

const required = [
  "README.md",
  "SECURITY.md",
  "package.json",
  "wrangler.jsonc",
  "wrangler.domain.jsonc",
  ".github/workflows/deploy.yml",
  ".github/workflows/verify.yml",
  "public/index.html",
  "public/404.html",
  "public/styles.css",
  "public/app.js",
  "public/product.json",
  "public/agents.txt",
  "public/llms.txt",
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

try {
  await text("public/evidence.json");
  failures.push("legacy evidence.json must not exist on the public launch surface");
} catch {}

const product = JSON.parse(await text("public/product.json"));
if (product.schemaVersion !== 1) failures.push("product schemaVersion must be 1");
if (product.name !== "PostSteward") failures.push("product name must be PostSteward");
if (product.publicOrigin !== publicOrigin) failures.push("product publicOrigin must be poststeward.com");
if (product.category !== "Agent-native continuous GTM for builders") failures.push("product category has drifted");
const interfaces = new Set(product.interfaces ?? []);
for (const value of ["CLI", "HTTP", "WebMCP"]) {
  if (!interfaces.has(value)) failures.push(`product interface missing: ${value}`);
}
if (!String(product.sourceDisclosure ?? "").includes("implementation source is not published")) {
  failures.push("product metadata must preserve the public/private source boundary");
}

const html = await text("public/index.html");
for (const marker of [
  "lang=\"en-GB\"",
  "<main id=\"main\"",
  "Keep building.",
  "Let your agent keep building the market.",
  "CLI / HTTP / WEBMCP",
  "Agent command centre",
  "Synthetic launch data",
  "Continuous GTM",
  `rel=\"canonical\" href=\"${publicOrigin}/\"`,
  `property=\"og:url\" content=\"${publicOrigin}/\"`
]) {
  if (!html.includes(marker)) failures.push(`HTML product/domain marker missing: ${marker}`);
}

const css = await text("public/styles.css");
if (!css.includes("prefers-reduced-motion")) failures.push("reduced-motion support is required");
if (!css.includes(":focus-visible")) failures.push("visible keyboard focus styles are required");

const app = await text("public/app.js");
if (/fetch\s*\(/.test(app)) failures.push("public demo JavaScript must remain effect-free and make no network calls");
if (!app.includes("Synthetic demo")) failures.push("interactive demo must keep its synthetic-result boundary explicit");

const workerConfig = JSON.parse(await text("wrangler.jsonc"));
if (workerConfig.name !== workerName) failures.push("workers.dev config must keep the launch Worker name");
if (workerConfig.workers_dev !== true) failures.push("workers.dev config must explicitly enable workers_dev");
if (workerConfig.preview_urls !== false) failures.push("preview URLs must remain disabled");
if (workerConfig.assets?.directory !== "./public") failures.push("workers.dev config must serve ./public");
if (workerConfig.routes) failures.push("workers.dev config must not attach production domains");

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
if (packageJson.engines?.node !== ">=24") failures.push("Node engine must stay >=24");
for (const command of [packageJson.scripts?.deploy, packageJson.scripts?.["deploy:domain"]]) {
  if (!command?.includes(`wrangler@${wranglerVersion}`)) failures.push(`deploy commands must pin Wrangler ${wranglerVersion}`);
}

const deployWorkflow = await text(".github/workflows/deploy.yml");
for (const marker of [
  `wrangler@${wranglerVersion}`,
  `CLOUDFLARE_ACCOUNT_ID: ${cloudflareAccountId}`,
  "CLOUDFLARE_API_TOKEN",
  "default: custom-domain",
  'mode="custom-domain"',
  "https://poststeward.com,https://www.poststeward.com",
  "persist-credentials: false",
  "WRANGLER_SEND_METRICS",
  "scripts/smoke-deployment.mjs"
]) {
  if (!deployWorkflow.includes(marker)) failures.push(`deployment workflow marker missing: ${marker}`);
}
if (deployWorkflow.includes("CLOUDFLARE_CUSTOM_DOMAIN_ENABLED")) failures.push("production domain must not depend on a feature toggle");
if (deployWorkflow.includes("vars.CLOUDFLARE_ACCOUNT_ID")) failures.push("Cloudflare account ID must use the pinned non-secret identifier");

const verifyWorkflow = await text(".github/workflows/verify.yml");
for (const marker of ["persist-credentials: false", "node-version: 24", "npm run verify", "node --check public/app.js"]) {
  if (!verifyWorkflow.includes(marker)) failures.push(`verification workflow marker missing: ${marker}`);
}

const headers = await text("public/_headers");
for (const marker of [
  "Strict-Transport-Security",
  "Content-Security-Policy",
  "X-Content-Type-Options: nosniff",
  "Referrer-Policy:",
  "X-Frame-Options: DENY",
  "Cross-Origin-Opener-Policy: same-origin",
  "Cross-Origin-Resource-Policy: same-origin",
  "Permissions-Policy:"
]) {
  if (!headers.includes(marker)) failures.push(`security header missing: ${marker}`);
}

const robots = await text("public/robots.txt");
if (!robots.includes(`${publicOrigin}/sitemap.xml`)) failures.push("robots.txt must advertise the public sitemap");
const sitemap = await text("public/sitemap.xml");
if (!sitemap.includes(`<loc>${publicOrigin}/</loc>`)) failures.push("sitemap must contain the public homepage");

async function walk(dir) {
  const out = [];
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory() && ![".git", "node_modules"].includes(entry.name)) out.push(...await walk(full));
    else if (entry.isFile() && [".js", ".mjs", ".html", ".json", ".md", ".yml", ".yaml", ".jsonc", ".txt", ".xml", ".svg"].includes(extname(entry.name))) out.push(full);
  }
  return out;
}

const forbidden = [
  { label: "private implementation repository identifier", pattern: /AyobamiH\/poststeward(?!-showcase)(?=\b|[\/#])/i },
  { label: "legacy canonical repository language", pattern: /canonical repository|canonical repo|canonicalRevision/i },
  { label: "private staging origin", pattern: /poststeward-staging\.woeinvests\.workers\.dev/i },
  { label: "provider access token name", pattern: /THREADS_ACCESS_TOKEN|LINKEDIN_ACCESS_TOKEN|STRIPE_SECRET_KEY/i },
  { label: "embedded bearer credential", pattern: /Authorization\s*:\s*["'`]Bearer\s+(?!<)/i },
  { label: "provider authority endpoint", pattern: /graph\.facebook\.com|api\.threads\.net|api\.x\.com|api\.linkedin\.com/i }
];

for (const file of await walk(rootPath)) {
  const rel = relative(rootPath, file);
  if (rel === "scripts/verify.mjs") continue;
  const content = await readFile(file, "utf8");
  for (const rule of forbidden) {
    if (rule.pattern.test(content)) failures.push(`${rule.label} exposed in ${rel}`);
  }
}

if (failures.length) {
  console.error("PostSteward launch verification failed:\n" + failures.map((failure) => `- ${failure}`).join("\n"));
  process.exit(1);
}

console.log(`PostSteward launch verification passed: ${product.category}; interfaces ${[...interfaces].join(", ")}; domain ${publicOrigin}.`);
