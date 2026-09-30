import { mkdir, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

const app = "https://app.poststeward.com";
const repository = "AyobamiH/poststeward";

async function boundedText(response) {
  if (!response.ok) throw new Error(`Release source returned HTTP ${response.status}`);
  const reader = response.body.getReader();
  const chunks = [];
  let size = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > 128 * 1024) throw new Error("Release source exceeds 128 KiB");
      chunks.push(value);
    }
  } finally { await reader.cancel().catch(() => {}); }
  return Buffer.concat(chunks).toString("utf8");
}

export async function syncRuntimeRelease({ send = fetch, output = new URL("../public/", import.meta.url), expected = process.env.POSTSTEWARD_RELEASE_REVISION } = {}) {
  if (expected && !/^[a-f0-9]{40}$/.test(expected)) throw new Error("Expected release must be an exact SHA");
  const get = async url => boundedText(await send(url, { redirect: "error", signal: AbortSignal.timeout(15000), headers: { "Cache-Control": "no-cache", "User-Agent": "poststeward-distribution" } }));
  const health = JSON.parse(await get(app + "/health"));
  const manifests = [];
  for (const [channel, origin] of [["stable", app], ["beta", "https://poststeward-staging.woeinvests.workers.dev"]]) {
    const manifest = JSON.parse(await get(origin + "/releases/" + channel + ".json"));
    if (manifest.schema_version !== 1 || manifest.product !== "poststeward" || manifest.channel !== channel ||
        !/^[a-f0-9]{40}$/.test(manifest.revision) || !/^[a-f0-9]{64}$/.test(manifest.runtime_tree_sha256) ||
        manifest.archive !== `https://github.com/${repository}/archive/${manifest.revision}.tar.gz` ||
        !Number.isFinite(Date.parse(manifest.expires_at)) || Date.parse(manifest.expires_at) <= Date.now()) throw new Error(`Invalid ${channel} runtime metadata`);
    if (channel === "stable" && (health.status !== "ok" || health.release !== manifest.revision || (expected && expected !== manifest.revision)))
      throw new Error("Stable metadata does not match the expected live production release");
    if (channel === "beta") {
      const betaHealth = JSON.parse(await get(origin + "/health"));
      if (betaHealth.status !== "ok" || betaHealth.release !== manifest.revision) throw new Error("Beta metadata does not match its live release");
    }
    manifests.push(manifest);
  }
  const revision = manifests[0].revision;
  const source = JSON.parse(await get(`https://api.github.com/repos/${repository}/contents/public/install.sh?ref=${revision}`));
  if (source.encoding !== "base64" || source.type !== "file") throw new Error("Canonical installer source is unavailable");
  const installer = Buffer.from(source.content.replaceAll("\n", ""), "base64").toString("utf8");
  if (!installer.startsWith("#!/usr/bin/env bash\n") || !installer.includes("https://app.poststeward.com") ||
      !installer.includes("runtime_tree_sha256") || installer.length > 64 * 1024) throw new Error("Canonical installer identity is invalid");
  // Compare the compiled/deployed asset with the same immutable source revision.
  if (await get(app + "/install.sh") !== installer) throw new Error("Deployed installer differs from the canonical release");
  await mkdir(new URL("releases/", output), { recursive: true });
  await writeFile(new URL("install.sh", output), installer);
  for (const manifest of manifests) await writeFile(new URL(`releases/${manifest.channel}.json`, output), JSON.stringify(manifest, null, 2) + "\n");
  return { revision, channels: manifests.map(value => value.channel), applicationOrigin: app };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  console.log("POSTSTEWARD_DISTRIBUTION " + JSON.stringify(await syncRuntimeRelease()));
}
