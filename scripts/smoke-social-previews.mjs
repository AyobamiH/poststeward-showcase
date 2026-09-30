import assert from "node:assert/strict";
import {pages, origin as canonicalOrigin, imagePath} from "./social-previews.mjs";
import {verifyPage, verifyPng} from "./verify-social-previews.mjs";
export async function verifySocialOrigin(origin, send = fetch) {
  const get = (path, type) => send(new URL(path, origin), {redirect:"manual",signal:AbortSignal.timeout(20000),headers:{"User-Agent":"Twitterbot/1.0","Accept":type,"Cache-Control":"no-cache"}});
  for (const page of pages) {
    const response = await get(page.path, "text/html");
    assert.equal(response.status, 200, page.path + " must be directly retrievable");
    assert.match(response.headers.get("content-type") || "", /text\/html/);
    verifyPage(await response.text(), page, canonicalOrigin);
  }
  const image = await get(imagePath, "image/png");
  assert.equal(image.status, 200, "Preview PNG must be retrievable without cookies or authentication");
  assert.match(image.headers.get("content-type") || "", /^image\/png(?:;|$)/);
  verifyPng(Buffer.from(await image.arrayBuffer()));
  for (const path of ["/og-image.svg", "/og-card.svg"]) {
    const response = await get(path, "image/*");
    assert.equal(response.status, 301, "Old SVG URL must redirect to the reviewed PNG");
    assert.equal(new URL(response.headers.get("location"), origin).href, new URL(imagePath, origin).href);
  }
  console.log("Initial-HTML social metadata, PNG retrieval and legacy image redirects verified at " + origin + "; this is not a platform rendering check.");
}
