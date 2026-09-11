const rawOrigins = process.env.SHOWCASE_ORIGINS;
if (!rawOrigins) throw new Error("SHOWCASE_ORIGINS is required");
const origins = rawOrigins.split(",").map((value) => value.trim()).filter(Boolean);
if (!origins.length || origins.some((origin) => !origin.startsWith("https://"))) throw new Error("SHOWCASE_ORIGINS must contain https URLs");
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const requiredHeaders = ["strict-transport-security", "content-security-policy", "x-content-type-options", "referrer-policy", "x-frame-options", "cross-origin-opener-policy", "cross-origin-resource-policy", "permissions-policy"];
const operationNames = ["workspace_status","accounts_list","account_disconnect","project_put","projects_list","campaign_create","campaign_get","campaign_validate","publish_now","schedule_create","schedule_cancel","schedule_replace","receipt_get","receipts_list","workspace_export","metrics_capture","publishing_pause","automation_configure","automation_inspect","automation_preview","automation_enable","automation_pause","billing_status","billing_quote","billing_checkout","billing_portal"];
const forbidden = /AyobamiH\/poststeward(?!-showcase)|poststeward-staging\.woeinvests\.workers\.dev/i;

async function getText(origin, path) {
  const response = await fetch(new URL(path, origin), { headers: { "cache-control": "no-cache" }, redirect: "follow" });
  if (!response.ok) throw new Error(`${path} returned ${response.status}`);
  const body = await response.text();
  if (forbidden.test(body)) throw new Error(`${path} exposes a private-source identifier`);
  return { response, body };
}

async function verifyOrigin(origin) {
  let lastError;
  for (let attempt = 1; attempt <= 12; attempt += 1) {
    try {
      const root = await getText(origin, "/");
      for (const header of requiredHeaders) if (!root.response.headers.get(header)) throw new Error(`root missing ${header}`);
      for (const marker of ["Let an agent post to X, Threads and LinkedIn", "Three agent paths, one operation catalogue", "[SHOWCASE MODE]", '<link rel="canonical" href="https://poststeward.com/"']) if (!root.body.includes(marker)) throw new Error(`root HTML missing marker: ${marker}`);

      const onboarding = await getText(origin, "/onboarding/");
      for (const marker of ["Four steps to give an agent publishing access", "Issue a scoped agent token", "Publish, then read the receipt"]) if (!onboarding.body.includes(marker)) throw new Error(`onboarding missing marker: ${marker}`);

      const guide = await getText(origin, "/agent-guide/");
      for (const marker of ["Everything an agent needs to publish and prove it", "Operation catalogue", "Browser WebMCP", "ambiguous_effect"]) if (!guide.body.includes(marker)) throw new Error(`agent guide missing marker: ${marker}`);

      const workspace = await getText(origin, "/workspace/");
      for (const marker of ["[SHOWCASE: NO EXTERNAL EFFECTS]", "Delivery receipts", "Agent access", "Advanced"]) if (!workspace.body.includes(marker)) throw new Error(`workspace preview missing marker: ${marker}`);

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
for (const origin of origins) await verifyOrigin(origin);
console.log(`Hosted PostSteward agent-surface verification passed for ${origins.length} origin(s).`);
