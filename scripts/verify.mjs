import { readFile, readdir } from "node:fs/promises";
import { extname, join, relative } from "node:path";

const root = new URL("../", import.meta.url);
const rootPath = root.pathname;
const publicOrigin = "https://poststeward.com";
const workerName = "poststeward-showcase";
const wranglerVersion = "4.130.0";
const cloudflareAccountId = "6ddcbcb8474f1a7e460b2f0aabec0e2f";
const operationNames = [
  "workspace_status", "accounts_list", "account_disconnect", "project_put",
  "projects_list", "campaign_create", "campaign_get", "campaign_validate",
  "publish_now", "schedule_create", "schedule_cancel", "schedule_replace",
  "receipt_get", "receipts_list", "workspace_export", "metrics_capture",
  "publishing_pause", "automation_configure", "automation_inspect",
  "automation_preview", "automation_enable", "automation_pause",
  "billing_status", "billing_quote", "billing_checkout", "billing_portal"
];

const required = [
  "README.md", "SECURITY.md", "package.json", "wrangler.jsonc",
  "wrangler.domain.jsonc", ".github/workflows/deploy.yml",
  ".github/workflows/verify.yml", "public/index.html", "public/404.html",
  "public/styles.css", "public/home.css", "public/home-composition.css", "public/public-pages.css", "public/favicon.svg", "public/og-image.svg", "public/app.js", "public/onboarding/index.html",
  "public/agent-guide/index.html", "public/workspace/index.html", "public/privacy/index.html", "public/terms/index.html", "public/data-deletion/index.html",
  "public/agent-guide.md", "public/product.json", "public/agents.txt",
  "public/llms.txt", "public/mcp.json", "public/help.json",
  "public/openapi.json", "public/docs/operations.md", "public/_headers",
  "public/robots.txt", "public/sitemap.xml", "scripts/smoke-deployment.mjs",
  "docs/ARCHITECTURE.md", "docs/CLOUDFLARE_DEPLOYMENT.md",
  "docs/LAUNCH_PLAN.md", "launch/PRODUCT_HUNT.md", "launch/OPENAI_SHOWCASE.md"
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


const favicon = await text("public/favicon.svg");
const legacyMark = await text("public/mark.svg");
if (legacyMark !== favicon) failures.push("legacy mark.svg must alias the canonical PostSteward favicon");
for (const path of ["public/index.html", "public/onboarding/index.html", "public/agent-guide/index.html", "public/workspace/index.html"]) {
  const page = await text(path);
  if (!page.includes('rel="icon" href="/favicon.svg?v=2"')) failures.push(`canonical versioned favicon missing: ${path}`);
  if (page.includes('/mark.svg')) failures.push(`legacy green favicon reference remains: ${path}`);
}

const product = JSON.parse(await text("public/product.json"));
if (product.schemaVersion !== 2) failures.push("product schemaVersion must be 2");
if (product.name !== "PostSteward") failures.push("product name must be PostSteward");
if (product.publicOrigin !== publicOrigin) failures.push("product publicOrigin must be poststeward.com");
if (product.category !== "Agent-first social publishing infrastructure for continuous GTM") failures.push("product category has drifted");
for (const value of ["Remote MCP", "HTTP", "CLI via HTTP", "WebMCP"]) {
  if (!(product.interfaces ?? []).includes(value)) failures.push(`product interface missing: ${value}`);
}
if (product.showcase?.effectfulPublicAccess !== false) failures.push("showcase must not claim effectful public access");
if (product.showcase?.credentialsAccepted !== false) failures.push("showcase must not accept credentials");
if (product.showcase?.billingEnabled !== false) failures.push("showcase billing must remain disabled until explicitly opened");
if (!String(product.sourceDisclosure ?? "").includes("implementation source is not published")) failures.push("product metadata must preserve the public/private source boundary");

const home = await text("public/index.html");
for (const marker of [
  "lang=\"en-GB\"", "<main id=\"main\" class=\"home home-organised\"", "Let agents publish.",
  "Keep proof of what happened.", "Receipts, not assumptions",
  "BUILT TO BE DISCOVERED BY SOFTWARE", "[SHOWCASE MODE]", "CLI via HTTP",
  "document.modelContext", `rel=\"canonical\" href=\"${publicOrigin}/\"`
]) if (!home.includes(marker)) failures.push(`homepage parity marker missing: ${marker}`);
if (home.includes('/auth/login')) failures.push("public showcase homepage must not link to the private sign-in surface");
if (!home.includes('href="/workspace/"')) failures.push("public showcase homepage must route workspace actions to the preview");
if (!home.includes('&lt;POSTSTEWARD_SERVICE_ORIGIN&gt;')) failures.push("homepage machine example must preserve the private service-origin placeholder");

const onboarding = await text("public/onboarding/index.html");
for (const marker of ["Four steps to give an agent publishing access", "Connect a publishing account", "Bind a project", "Issue a scoped agent token", "Publish, then read the receipt", "<POSTSTEWARD_SERVICE_ORIGIN>"]) {
  if (!onboarding.includes(marker)) failures.push(`onboarding parity marker missing: ${marker}`);
}

const guide = await text("public/agent-guide/index.html");
for (const marker of ["Everything an agent needs to publish and prove it", "Operation catalogue", "Browser WebMCP", "schedule_cancel", "metrics_capture", "ambiguous_effect", "Limits and retention"]) {
  if (!guide.includes(marker)) failures.push(`agent guide parity marker missing: ${marker}`);
}

const workspace = await text("public/workspace/index.html");
for (const marker of ["[SHOWCASE: NO EXTERNAL EFFECTS]", "Connect an account", "Bind a project", "Submit exact copy", "Delivery receipts", "Agent access", "Advanced", "Token display is intentionally unavailable"]) {
  if (!workspace.includes(marker)) failures.push(`workspace parity marker missing: ${marker}`);
}


const privacy = await text("public/privacy/index.html");
for (const marker of ["Privacy Policy", "Provider credentials are encrypted", "community@oneclickpostfactory.com", 'href="/data-deletion/"']) {
  if (!privacy.includes(marker)) failures.push(`privacy page marker missing: ${marker}`);
}
const terms = await text("public/terms/index.html");
for (const marker of ["Terms of Service", "Agent authority", "External providers", "laws of England and Wales"]) {
  if (!terms.includes(marker)) failures.push(`terms page marker missing: ${marker}`);
}
const deletion = await text("public/data-deletion/index.html");
for (const marker of ["User data deletion", "PostSteward data deletion request", "minimal completed-deletion tombstone", "Threads / Meta"]) {
  if (!deletion.includes(marker)) failures.push(`data-deletion page marker missing: ${marker}`);
}
for (const page of [privacy, terms, deletion]) {
  if (!page.includes('href="/favicon.svg?v=2"')) failures.push("legal page must use canonical versioned favicon");
  if (page.includes("/mark.svg")) failures.push("legal page must not use legacy green favicon");
}

const mcp = JSON.parse(await text("public/mcp.json"));
if (mcp.effectfulPublicEndpoint !== false) failures.push("mcp metadata must remain documentation-only on the showcase");
if (mcp.operationCount !== operationNames.length) failures.push(`mcp operationCount must be ${operationNames.length}`);
const mcpNames = new Set((mcp.operations ?? []).map((operation) => operation.name));
for (const name of operationNames) if (!mcpNames.has(name)) failures.push(`mcp operation missing: ${name}`);
if (mcp.transports?.cli?.kind !== "shell over HTTP") failures.push("CLI must be described accurately as shell over HTTP");
if (!String(mcp.transports?.webMcp?.api ?? "").includes("document.modelContext")) failures.push("WebMCP metadata must expose the browser API surface");

const help = JSON.parse(await text("public/help.json"));
if (help.operationCount !== operationNames.length) failures.push("help operation count must match catalogue");
if (help.showcase !== true) failures.push("help metadata must state showcase mode");

const openapi = JSON.parse(await text("public/openapi.json"));
if (openapi.openapi !== "3.1.0") failures.push("OpenAPI document must use 3.1.0");
if (openapi["x-poststeward-showcase"]?.effectfulPublicServer !== false) failures.push("OpenAPI must not imply a live public effectful server");
const operationEnum = openapi.paths?.["/api/operations/{operation}"]?.post?.parameters?.find((item) => item.name === "operation")?.schema?.enum ?? [];
if (operationEnum.length !== operationNames.length) failures.push("OpenAPI operation enum must match the 26-operation catalogue");
for (const name of operationNames) if (!operationEnum.includes(name)) failures.push(`OpenAPI operation missing: ${name}`);

const agentMarkdown = await text("public/agent-guide.md");
for (const marker of ["# PostSteward agent guide", "Remote MCP", "Browser WebMCP", "## Operation catalogue", "`publish_now`", "`ambiguous_effect`", "## Limits and retention"]) {
  if (!agentMarkdown.includes(marker)) failures.push(`agent Markdown marker missing: ${marker}`);
}
const agentsTxt = await text("public/agents.txt");
if (!agentsTxt.includes("Never blindly retry an ambiguous_effect")) failures.push("agents.txt must preserve the no-blind-retry rule");
const llmsTxt = await text("public/llms.txt");
for (const marker of ["Remote MCP", "CLI: shell/cURL calls", "WebMCP", "effectful public service origin"]) {
  if (!llmsTxt.includes(marker)) failures.push(`llms.txt marker missing: ${marker}`);
}

const css = await text("public/styles.css");
for (const marker of ["--primary:oklch(0.8 0.145 82)", "JetBrains Mono", "repeating-linear-gradient", ":focus-visible", "prefers-reduced-motion", ".terminal-shell"]) {
  if (!css.includes(marker)) failures.push(`scaffold design marker missing: ${marker}`);
}
const homeCss = await text("public/home.css");
for (const marker of ["--brand: #ff6847", "--bg-canvas:", ".button.primary", ".machine-label"]) {
  if (!homeCss.includes(marker)) failures.push(`staging-home design marker missing: ${marker}`);
}
const homeComposition = await text("public/home-composition.css");
for (const marker of [".hero-organised", ".control-map", ".agent-surface", ".pricing-organised"]) {
  if (!homeComposition.includes(marker)) failures.push(`staging-home composition marker missing: ${marker}`);
}

const publicPagesCss = await text("public/public-pages.css");
for (const marker of [".public-page-header", ".public-page-main", ".public-section", "var(--brand)", "var(--bg-canvas)"]) {
  if (!publicPagesCss.includes(marker)) failures.push(`staging public-page visual marker missing: ${marker}`);
}
for (const path of [
  "public/onboarding/index.html",
  "public/agent-guide/index.html",
  "public/workspace/index.html",
  "public/privacy/index.html",
  "public/terms/index.html",
  "public/data-deletion/index.html",
]) {
  const page = await text(path);
  if (!page.includes('href="/home.css"') || !page.includes('href="/public-pages.css"'))
    failures.push(`public page not using staging visual system: ${path}`);
  if (!page.includes('class="public-page"') || !page.includes('class="public-page-header"'))
    failures.push(`public page shell drifted from staging visual system: ${path}`);
  if (/terminal-shell|status-strip|header-main|href="\/styles\.css"|\/mark\.svg/.test(page))
    failures.push(`legacy terminal visual system remains in ${path}`);
}

const app = await text("public/app.js");
if (/fetch\s*\(/.test(app)) failures.push("showcase JavaScript must remain effect-free and make no network calls");
if (!app.includes("Showcase preview only")) failures.push("preview actions must keep their non-effectful boundary explicit");

const workerConfig = JSON.parse(await text("wrangler.jsonc"));
if (workerConfig.name !== workerName) failures.push("workers.dev config must keep the launch Worker name");
if (workerConfig.workers_dev !== true) failures.push("workers.dev config must explicitly enable workers_dev");
if (workerConfig.preview_urls !== false) failures.push("workers.dev preview URLs must remain disabled");
if (workerConfig.assets?.directory !== "./public") failures.push("workers.dev config must serve ./public");
if (workerConfig.routes) failures.push("workers.dev config must not attach production domains");

const domainConfig = JSON.parse(await text("wrangler.domain.jsonc"));
if (domainConfig.name !== workerName) failures.push("custom-domain config must deploy the same Worker name");
if (domainConfig.workers_dev !== false) failures.push("custom-domain config must disable workers.dev");
if (domainConfig.preview_urls !== false) failures.push("custom-domain preview URLs must remain disabled");
if (domainConfig.assets?.directory !== "./public") failures.push("custom-domain config must serve ./public");
const expectedDomains = ["poststeward.com", "www.poststeward.com"];
const configuredDomains = (domainConfig.routes ?? []).map((route) => route.pattern).sort();
if (JSON.stringify(configuredDomains) !== JSON.stringify([...expectedDomains].sort())) failures.push(`custom-domain config must contain exactly: ${expectedDomains.join(", ")}`);
for (const route of domainConfig.routes ?? []) if (route.custom_domain !== true) failures.push(`production hostname must be a Cloudflare Custom Domain: ${route.pattern}`);

const packageJson = JSON.parse(await text("package.json"));
if (packageJson.engines?.node !== ">=24") failures.push("Node engine must stay >=24");
for (const command of [packageJson.scripts?.deploy, packageJson.scripts?.["deploy:domain"]]) if (!command?.includes(`wrangler@${wranglerVersion}`)) failures.push(`deploy commands must pin Wrangler ${wranglerVersion}`);

const deployWorkflow = await text(".github/workflows/deploy.yml");
for (const marker of [`wrangler@${wranglerVersion}`, `CLOUDFLARE_ACCOUNT_ID: ${cloudflareAccountId}`, "CLOUDFLARE_API_TOKEN", "default: custom-domain", 'mode="custom-domain"', "https://poststeward.com,https://www.poststeward.com", "persist-credentials: false", "WRANGLER_SEND_METRICS", "scripts/smoke-deployment.mjs"]) {
  if (!deployWorkflow.includes(marker)) failures.push(`deployment workflow marker missing: ${marker}`);
}
if (deployWorkflow.includes("CLOUDFLARE_CUSTOM_DOMAIN_ENABLED")) failures.push("production domain must not depend on a feature toggle");
if (deployWorkflow.includes("vars.CLOUDFLARE_ACCOUNT_ID")) failures.push("Cloudflare account ID must use the pinned non-secret identifier");

const verifyWorkflow = await text(".github/workflows/verify.yml");
for (const marker of ["persist-credentials: false", "node-version: 24", "npm run verify", "node --check public/app.js", "node --check scripts/smoke-deployment.mjs"]) if (!verifyWorkflow.includes(marker)) failures.push(`verification workflow marker missing: ${marker}`);

const headers = await text("public/_headers");
for (const marker of ["Strict-Transport-Security", "Content-Security-Policy", "X-Content-Type-Options: nosniff", "Referrer-Policy:", "X-Frame-Options: DENY", "Cross-Origin-Opener-Policy: same-origin", "Cross-Origin-Resource-Policy: same-origin", "Permissions-Policy:"]) if (!headers.includes(marker)) failures.push(`security header missing: ${marker}`);

const robots = await text("public/robots.txt");
if (!robots.includes("Disallow: /workspace/")) failures.push("robots.txt must keep the synthetic workspace out of search results");
if (!robots.includes(`${publicOrigin}/sitemap.xml`)) failures.push("robots.txt must advertise the public sitemap");
const sitemap = await text("public/sitemap.xml");
for (const url of [`${publicOrigin}/`, `${publicOrigin}/onboarding/`, `${publicOrigin}/agent-guide/`, `${publicOrigin}/privacy/`, `${publicOrigin}/terms/`, `${publicOrigin}/data-deletion/`]) if (!sitemap.includes(`<loc>${url}</loc>`)) failures.push(`sitemap missing: ${url}`);

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
  { label: "private UI source identifier", pattern: /bright-post-dash(?:\.lovable\.dev)?/i },
  { label: "provider access token name", pattern: /THREADS_ACCESS_TOKEN|LINKEDIN_ACCESS_TOKEN|STRIPE_SECRET_KEY/i },
  { label: "embedded bearer credential", pattern: /Authorization\s*:\s*["'`]Bearer\s+(?!<)/i },
  { label: "provider authority endpoint", pattern: /graph\.facebook\.com|api\.threads\.net|api\.x\.com|api\.linkedin\.com/i }
];
for (const file of await walk(rootPath)) {
  const rel = relative(rootPath, file);
  if (rel === "scripts/verify.mjs") continue;
  const content = await readFile(file, "utf8");
  for (const rule of forbidden) if (rule.pattern.test(content)) failures.push(`${rule.label} exposed in ${rel}`);
}

if (failures.length) {
  console.error("PostSteward showcase verification failed:\n" + failures.map((failure) => `- ${failure}`).join("\n"));
  process.exit(1);
}
console.log(`PostSteward showcase verification passed: scaffold parity, ${operationNames.length} operations, MCP/HTTP/CLI-via-HTTP/WebMCP discovery, effect-free preview, domain ${publicOrigin}.`);
