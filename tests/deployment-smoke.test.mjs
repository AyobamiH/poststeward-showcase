import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { verifyOrigin } from "../scripts/smoke-deployment.mjs";

const origin = "https://poststeward.com";
const securityHeaders = Object.fromEntries(["strict-transport-security", "content-security-policy", "x-content-type-options", "referrer-policy", "x-frame-options", "cross-origin-opener-policy", "cross-origin-resource-policy", "permissions-policy"].map(name => [name, "present"]));
function client({ omitOperation, wrongCount, staleOnce = false } = {}) {
  let stale = staleOnce;
  return async (url, options) => {
    const parsed = new URL(url);
    const path = parsed.pathname;
    if (parsed.protocol === "http:") return new Response(null, { status: 301, headers: { location: origin + "/" } });
    if (["/og-image.svg", "/og-card.svg"].includes(path)) return new Response(null, { status: 301, headers: { location: "/social/poststeward-v2.png" } });
    if (path === "/install.sh") return new Response("#!/usr/bin/env bash\n# https://app.poststeward.com\n");
    if (path.startsWith("/releases/")) return Response.json({ product: "poststeward", channel: path.includes("stable") ? "stable" : "beta", revision: "a".repeat(40), runtime_tree_sha256: "b".repeat(64), expires_at: "2099-01-01T00:00:00Z" });
    const file = path.endsWith("/") ? path + "index.html" : path;
    let body = await readFile(new URL("../public" + file, import.meta.url));
    if (path === "/mcp.json") {
      const value = JSON.parse(body);
      if (omitOperation) value.operations = value.operations.filter(operation => operation.name !== omitOperation);
      if (wrongCount) value.operationCount = 34;
      body = JSON.stringify(value);
    }
    if (path === "/install/" && stale && options?.headers?.["User-Agent"] === "Twitterbot/1.0") {
      stale = false;
      body = body.toString().replaceAll("Install on Linux, macOS 15/26 or WSL 2/Ubuntu 24.04. Pair your machine and review activation before local publishing.", "Old edge metadata");
    }
    return new Response(body, { headers: { ...securityHeaders, "content-type": path.endsWith(".png") ? "image/png" : "text/html" } });
  };
}
test("deployment verifies the complete 46-operation catalogue and all social routes", async () => {
  await verifyOrigin(origin, { send: client(), attempts: 1 });
  for (const overrides of [{ omitOperation: "preparation_approve" }, { wrongCount: true }]) {
    await assert.rejects(verifyOrigin(origin, { send: client(overrides), attempts: 1 }), /mcp\.json/);
  }
});
test("social metadata propagation retries within the bounded deployment convergence loop", async () => {
  let waits = 0;
  await verifyOrigin(origin, { send: client({ staleOnce: true }), attempts: 2, wait: async ms => { assert.equal(ms, 10000); waits++; } });
  assert.equal(waits, 1);
});
