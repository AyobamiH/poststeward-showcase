import { readFile, readdir } from "node:fs/promises";
import { extname, join, relative } from "node:path";

const root = new URL("../", import.meta.url);
const rootPath = root.pathname;
const canonicalPrefix = "https://github.com/AyobamiH/poststeward";

const required = [
  "README.md",
  "SECURITY.md",
  "public/index.html",
  "public/styles.css",
  "public/app.js",
  "public/evidence.json",
  "docs/ARCHITECTURE.md",
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
for (const marker of ["lang=\"en-GB\"", "<main id=\"main\">", "Simulation only", "Canonical repo", "meta name=\"viewport\""]) {
  if (!html.includes(marker)) failures.push(`HTML accessibility/boundary marker missing: ${marker}`);
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

async function walk(dir) {
  const out = [];
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory() && ![".git", "node_modules"].includes(entry.name)) out.push(...await walk(full));
    else if (entry.isFile() && [".js", ".mjs", ".html", ".json", ".md", ".yml", ".yaml", ".jsonc"].includes(extname(entry.name))) out.push(full);
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

console.log(`Showcase verification passed: ${evidence.facts.length} evidence facts, canonical ${evidence.canonicalRevision.slice(0, 8)}.`);
