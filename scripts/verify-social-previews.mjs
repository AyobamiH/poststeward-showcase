import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { pages, origin, imagePath, imageAlt } from "./social-previews.mjs";
const decode = text => text.replaceAll("&quot;", '"').replaceAll("&#39;", "'").replaceAll("&lt;", "<").replaceAll("&gt;", ">").replaceAll("&amp;", "&");
export function readHead(html) {
  const head = html.match(/<head\b[^>]*>([\s\S]*?)<\/head>/i)?.[1];
  assert.ok(head, "Initial HTML must contain a head");
  const tags = [...head.matchAll(/<(meta|link)\b[^>]*>/gi)].map(([raw, tag]) => ({ tag: tag.toLowerCase(), attributes: Object.fromEntries([...raw.matchAll(/([\w:-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')/g)].map(([, name, a, b]) => [name.toLowerCase(), decode(a ?? b)])) }));
  return { head, tags, title: decode(head.match(/<title>([\s\S]*?)<\/title>/i)?.[1] || "") };
}
export function verifyPage(html, page, expectedOrigin = origin) {
  const {head, tags, title} = readHead(html);
  const value = key => {
    const matches = tags.filter(x => x.tag === "meta" && (x.attributes.property === key || x.attributes.name === key));
    assert.equal(matches.length, 1, "Exactly one " + key);
    return matches[0].attributes.content;
  };
  const canonical = tags.filter(x => x.tag === "link" && x.attributes.rel === "canonical");
  assert.equal(canonical.length, 1, "Exactly one canonical URL");
  assert.equal(canonical[0].attributes.href, expectedOrigin + page.path);
  assert.equal(title, page.title);
  for (const key of ["og:title", "twitter:title"]) assert.equal(value(key), page.title);
  for (const key of ["description", "og:description", "twitter:description"]) assert.equal(value(key), page.description);
  assert.equal(value("og:url"), expectedOrigin + page.path);
  assert.equal(value("og:type"), "website");
  assert.equal(value("og:site_name"), "PostSteward");
  assert.equal(value("og:locale"), "en_GB");
  for (const key of ["og:image", "og:image:secure_url", "twitter:image"]) assert.equal(value(key), expectedOrigin + imagePath);
  for (const key of ["og:image:alt", "twitter:image:alt"]) assert.equal(value(key), imageAlt);
  assert.equal(value("og:image:type"), "image/png");
  assert.equal(value("og:image:width"), "1200"); assert.equal(value("og:image:height"), "630");
  assert.equal(value("twitter:card"), "summary_large_image");
  assert.ok(html.indexOf('property="og:image"') < 65536, "Metadata must be early in the initial HTML");
  assert.doesNotMatch(head, /og-image\.svg|og-card\.svg|PRIVATE_PREVIEW_SENTINEL|product_threads|example_product|access_token=|oauth_code=|session_id=/i);
  return true;
}
export function verifyPng(bytes) {
  assert.ok(bytes.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])), "Social image must be a real PNG");
  assert.equal(bytes.readUInt32BE(16), 1200); assert.equal(bytes.readUInt32BE(20), 630);
  assert.ok(bytes.length > 1024 && bytes.length < 1024 * 1024, "Branded PNG must be bounded below 1 MiB");
}
export async function verifySocialPreviews() {
  for (const page of pages) verifyPage(await readFile(new URL("../public/" + page.file, import.meta.url), "utf8"), page);
  verifyPng(await readFile(new URL("../public" + imagePath, import.meta.url)));
  const robots = await readFile(new URL("../public/robots.txt", import.meta.url), "utf8");
  assert.doesNotMatch(robots, /Disallow:\s*\/social/);
  assert.doesNotMatch(robots, /Disallow:\s*\/workspace/);
  const demo = await readFile(new URL("../public/workspace/index.html", import.meta.url), "utf8");
  assert.match(demo, /name="robots" content="noindex,nofollow"/);
  console.log("Social metadata verified on " + pages.length + " initial-HTML routes; bounded 1200×630 PNG and privacy-safe previews.");
}
if (process.argv[1] === fileURLToPath(import.meta.url)) await verifySocialPreviews();
