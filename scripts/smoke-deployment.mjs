const rawOrigins = process.env.SHOWCASE_ORIGINS;
if (!rawOrigins) throw new Error("SHOWCASE_ORIGINS is required");

const origins = rawOrigins.split(",").map((value) => value.trim()).filter(Boolean);
if (!origins.length || origins.some((origin) => !origin.startsWith("https://"))) {
  throw new Error("SHOWCASE_ORIGINS must contain https URLs");
}

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
const requiredInterfaces = new Set(["CLI", "HTTP", "WebMCP"]);

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
      for (const marker of [
        "PostSteward",
        "Keep building.",
        "Let your agent keep building the market.",
        "CLI / HTTP / WEBMCP",
        "Synthetic launch data",
        '<link rel="canonical" href="https://poststeward.com/"'
      ]) {
        if (!html.includes(marker)) throw new Error(`root HTML missing marker: ${marker}`);
      }
      if (/AyobamiH\/poststeward(?!-showcase)/i.test(html)) {
        throw new Error("root HTML exposes a private implementation repository identifier");
      }

      const productResponse = await fetch(new URL("/product.json", origin), {
        headers: { "cache-control": "no-cache" }
      });
      if (!productResponse.ok) throw new Error(`product metadata returned ${productResponse.status}`);
      const product = await productResponse.json();
      if (product.category !== "Agent-native continuous GTM for builders") {
        throw new Error("product category does not match launch positioning");
      }
      const interfaces = new Set(product.interfaces ?? []);
      for (const value of requiredInterfaces) {
        if (!interfaces.has(value)) throw new Error(`product metadata missing interface: ${value}`);
      }

      console.log(`Hosted PostSteward verified at ${origin} on attempt ${attempt}; final URL ${response.url}.`);
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
console.log(`Hosted PostSteward verification passed for ${origins.length} origin(s).`);
