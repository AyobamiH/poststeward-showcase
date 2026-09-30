const rawOrigins = process.env.SHOWCASE_ORIGINS;
const { verifySocialOrigin } = await import("./smoke-social-previews.mjs");
if (!rawOrigins) throw new Error("SHOWCASE_ORIGINS is required");
const origins = rawOrigins.split(",").map((value) => value.trim()).filter(Boolean);
if (!origins.length || origins.some((origin) => !origin.startsWith("https://"))) throw new Error("SHOWCASE_ORIGINS must contain https URLs");
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const requiredHeaders = ["strict-transport-security", "content-security-policy", "x-content-type-options", "referrer-policy", "x-frame-options", "cross-origin-opener-policy", "cross-origin-resource-policy", "permissions-policy"];
const operationNames = [
  "workspace_status",
  "publishing_capabilities",
  "accounts_list",
  "account_disconnect",
  "project_put",
  "projects_list",
  "campaign_create",
  "campaign_get",
  "campaign_validate",
  "publish_now",
  "schedule_create",
  "schedule_cancel",
  "delivery_approve",
  "delivery_reject",
  "schedule_replace",
  "receipt_get",
  "receipt_recheck",
  "receipts_list",
  "workspace_export",
  "metrics_capture",
  "publishing_pause",
  "automation_configure",
  "automation_inspect",
  "automation_preview",
  "automation_enable",
  "automation_pause",
  "billing_status",
  "billing_quote",
  "billing_checkout",
  "billing_portal",
  "runtime_inspect",
  "runtime_schedule_create",
  "runtime_schedule_cancel",
  "runtime_command_get"
];
const forbidden = /AyobamiH\/poststeward(?!-showcase)|poststeward-staging\.woeinvests\.workers\.dev/i;

async function getText(origin, path) {
  const response = await fetch(new URL(path, origin), { headers: { "cache-control": "no-cache" }, redirect: "follow" });
  if (!response.ok) throw new Error(`${path} returned ${response.status}`);
  const body = await response.text();
  const boundaryBody = path === "/install.sh" ? body.replaceAll("AyobamiH/poststeward", "released-runtime") : body;
  if (forbidden.test(boundaryBody)) throw new Error(`${path} exposes a private-source identifier`);
  return { response, body };
}

async function verifyOrigin(origin) {
  let lastError;
  for (let attempt = 1; attempt <= 12; attempt += 1) {
    try {
      const root = await getText(origin, "/");
      for (const header of requiredHeaders) if (!root.response.headers.get(header)) throw new Error(`root missing ${header}`);
      for (const marker of ["Let agents publish.", "Keep proof of what happened.", "Start free", 'href="https://app.poststeward.com/auth/login"', '<link rel="canonical" href="https://poststeward.com/"']) if (!root.body.includes(marker)) throw new Error(`root HTML missing marker: ${marker}`);

      const installer = await getText(origin, "/install.sh");
      if (!installer.body.startsWith("#!/usr/bin/env bash\n") || !installer.body.includes("https://app.poststeward.com")) throw new Error("canonical installer missing/wrong application origin");
      for (const channel of ["stable", "beta"]) {
        const response = await fetch(new URL(`/releases/${channel}.json`, origin), { headers: { "cache-control": "no-cache" } });
        if (!response.ok) throw new Error(`${channel} metadata returned ${response.status}`);
        const value = await response.json();
        if (value.product !== "poststeward" || value.channel !== channel || !/^[a-f0-9]{40}$/.test(value.revision) || !/^[a-f0-9]{64}$/.test(value.runtime_tree_sha256) || Date.parse(value.expires_at) <= Date.now()) throw new Error(`${channel} distribution metadata invalid`);
      }
      const installGuide = await getText(origin, "/install/");
      for (const marker of ["Install the full PostSteward runtime", "poststeward cloud bridge", "poststeward cloud recovery-review"]) if (!installGuide.body.includes(marker)) throw new Error(`installation guide missing ${marker}`);
      const onboarding = await getText(origin, "/onboarding/");
      for (const marker of ["Start publishing with PostSteward", "Connect a publishing account", "Create a publishing project", "Review, schedule and check the result", "Optional: connect an agent", "Owner approval comes before agent publication"]) if (!onboarding.body.includes(marker)) throw new Error(`onboarding missing marker: ${marker}`);

      const guide = await getText(origin, "/agent-guide/");
      for (const marker of ["Everything an agent needs to publish and prove it", "Operation catalogue", "Browser WebMCP", "ambiguous_effect"]) if (!guide.body.includes(marker)) throw new Error(`agent guide missing marker: ${marker}`);

      const workspace = await getText(origin, "/workspace/");
      for (const marker of ["Demo · sample data", "Delivery receipts", "Agent access", "Advanced"]) if (!workspace.body.includes(marker)) throw new Error(`workspace preview missing marker: ${marker}`);


      const privacy = await getText(origin, "/privacy/");
      for (const marker of ["Privacy Policy", "Provider credentials are encrypted", "community@oneclickpostfactory.com"]) if (!privacy.body.includes(marker)) throw new Error(`privacy missing marker: ${marker}`);

      const terms = await getText(origin, "/terms/");
      for (const marker of ["Terms of Service", "Agent authority", "External providers"]) if (!terms.body.includes(marker)) throw new Error(`terms missing marker: ${marker}`);

      const deletion = await getText(origin, "/data-deletion/");
      for (const marker of ["User data deletion", "PostSteward data deletion request", "Threads / Meta"]) if (!deletion.body.includes(marker)) throw new Error(`data deletion missing marker: ${marker}`);

      const markdown = await getText(origin, "/agent-guide.md");
      if (!markdown.body.includes("## Operation catalogue") || !markdown.body.includes("`publish_now`")) throw new Error("agent-guide.md is incomplete");
      const agents = await getText(origin, "/agents.txt");
      if (!agents.body.includes("Never blindly retry an ambiguous_effect")) throw new Error("agents.txt lost retry safety rule");
      const llms = await getText(origin, "/llms.txt");
      if (!llms.body.includes("CLI: shell/cURL calls") || !llms.body.includes("WebMCP")) throw new Error("llms.txt lost agent transport discovery");

      const mcpResponse = await fetch(new URL("/mcp.json", origin), { headers: { "cache-control": "no-cache" } });
      if (!mcpResponse.ok) throw new Error(`mcp.json returned ${mcpResponse.status}`);
      const mcpText = await mcpResponse.text();
      if (forbidden.test(mcpText)) throw new Error("mcp.json exposes a private-source identifier");
      const mcp = JSON.parse(mcpText);
      if (mcp.effectfulPublicEndpoint !== false) throw new Error("mcp.json incorrectly claims an effectful public endpoint");
      if (mcp.operationCount !== operationNames.length) throw new Error("mcp.json operation count drifted");
      const names = new Set((mcp.operations ?? []).map((operation) => operation.name));
      for (const name of operationNames) if (!names.has(name)) throw new Error(`mcp.json missing ${name}`);

      for (const path of ["/help.json", "/openapi.json", "/docs/operations.md"]) await getText(origin, path);
      console.log(`Hosted PostSteward agent surface verified at ${origin} on attempt ${attempt}; final URL ${root.response.url}.`);
      return;
    } catch (error) {
      lastError = error;
      console.log(`Hosted verification ${origin} attempt ${attempt}/12 did not converge: ${error.message}`);
      if (attempt < 12) await sleep(10_000);
    }
  }
  throw lastError;
}
for (const origin of origins) {
  await verifyOrigin(origin);
  await verifySocialOrigin(origin);
}
console.log(`Hosted PostSteward agent-surface verification passed for ${origins.length} origin(s).`);
