const configuredOrigins = process.env.SHOWCASE_ORIGINS ?? process.env.SHOWCASE_ORIGIN;
if (!configuredOrigins) {
  throw new Error("SHOWCASE_ORIGINS or SHOWCASE_ORIGIN must be configured");
}

const origins = [...new Set(
  configuredOrigins
    .split(",")
    .map((origin) => origin.trim())
    .filter(Boolean)
)];

if (!origins.length || origins.some((origin) => !origin.startsWith("https://"))) {
  throw new Error("all showcase origins must be https URLs");
}

const canonicalOrigin = "https://poststeward.com";
const canonicalMarker = `<link rel="canonical" href="${canonicalOrigin}/"`;
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const requiredHeaders = [
  "strict-transport-security",
  "content-security-policy",
  "x-content-type-options",
  "referrer-policy",
  "x-frame-options",
  "cross-origin-opener-policy",
  "cross-origin-resource-policy",
  "permissions-policy"
];

async function verifyOrigin(origin) {
  let lastError;
  for (let attempt = 1; attempt <= 12; attempt += 1) {
    try {
      const response = await fetch(origin, {
        redirect: "follow",
        headers: { "cache-control": "no-cache" }
      });
      if (!response.ok) throw new Error(`root returned ${response.status}`);

      for (const header of requiredHeaders) {
        if (!response.headers.get(header)) throw new Error(`missing ${header}`);
      }

      const html = await response.text();
      if (!html.includes("PostSteward") || !html.includes("Simulation only")) {
        throw new Error("root HTML does not match showcase markers");
      }
      if (!html.includes(canonicalMarker)) {
        throw new Error(`root HTML does not declare ${canonicalOrigin}/ as canonical`);
      }

      const evidenceResponse = await fetch(new URL("/evidence.json", response.url), {
        redirect: "follow",
        headers: { "cache-control": "no-cache" }
      });
      if (!evidenceResponse.ok) throw new Error(`evidence returned ${evidenceResponse.status}`);
      const evidence = await evidenceResponse.json();
      if (!/^[0-9a-f]{40}$/.test(evidence.canonicalRevision ?? "")) {
        throw new Error("hosted evidence has no canonical revision");
      }

      console.log(`Hosted showcase verified at ${origin} on attempt ${attempt}; final URL ${response.url}.`);
      return;
    } catch (error) {
      lastError = error;
      console.log(`Hosted verification for ${origin} attempt ${attempt}/12 did not converge: ${error.message}`);
      if (attempt < 12) await sleep(10_000);
    }
  }

  throw lastError;
}

for (const origin of origins) {
  await verifyOrigin(origin);
}

console.log(`Hosted showcase verification passed for ${origins.length} origin(s).`);
