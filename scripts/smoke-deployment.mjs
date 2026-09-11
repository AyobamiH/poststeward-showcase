const origin = process.env.SHOWCASE_ORIGIN;
if (!origin || !origin.startsWith("https://")) {
  throw new Error("SHOWCASE_ORIGIN must be an https URL");
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const requiredHeaders = [
  "content-security-policy",
  "x-content-type-options",
  "referrer-policy"
];

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

    const evidenceResponse = await fetch(new URL("/evidence.json", origin), {
      headers: { "cache-control": "no-cache" }
    });
    if (!evidenceResponse.ok) throw new Error(`evidence returned ${evidenceResponse.status}`);
    const evidence = await evidenceResponse.json();
    if (!/^[0-9a-f]{40}$/.test(evidence.canonicalRevision ?? "")) {
      throw new Error("hosted evidence has no canonical revision");
    }

    console.log(`Hosted showcase verified at ${origin} on attempt ${attempt}.`);
    process.exit(0);
  } catch (error) {
    lastError = error;
    console.log(`Hosted verification attempt ${attempt}/12 did not converge: ${error.message}`);
    if (attempt < 12) await sleep(10_000);
  }
}

throw lastError;
