import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

// Public, read-only source of truth; no workspace token or owner session is used.
const endpoint = "https://app.poststeward.com/help.json";
const catalogue = JSON.parse(await readFile(new URL("../public/catalog.json", import.meta.url), "utf8"));
let response;
for (let attempt = 1; attempt <= 3; attempt += 1) {
  try {
    response = await fetch(endpoint, {
      redirect: "error",
      cache: "no-store",
      headers: { "cache-control": "no-cache", "accept": "application/json" },
      signal: AbortSignal.timeout(15_000),
    });
    if (response.status === 200 && (response.headers.get("content-type") || "").includes("application/json")) break;
    throw new Error(`hosted catalogue status ${response.status}`);
  } catch (error) {
    if (attempt === 3) throw new Error(`Cannot verify live operation contract: ${error.message}`);
    await new Promise((resolve) => setTimeout(resolve, 1500));
  }
}
const source = await response.json();
assert.ok(Array.isArray(source.operations), "hosted operation catalogue missing");
const reviewed = source.operations.map(({ availability, ...operation }) => operation);
assert.deepStrictEqual(reviewed, catalogue, "Showcase operation schema, consequence or scope drifted from the hosted application");
console.log(JSON.stringify({ status: "PASS", contract: "PostSteward public operation catalogue", operations: reviewed.length, origin: endpoint }));
