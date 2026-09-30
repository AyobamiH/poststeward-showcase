import test from "node:test";
import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import {pages} from "../scripts/social-previews.mjs";
import {verifyPage, verifyPng, verifySocialPreviews} from "../scripts/verify-social-previews.mjs";
import {verifySocialOrigin} from "../scripts/smoke-social-previews.mjs";
test("every maintained shareable HTML route has one accurate initial-HTML preview and a real image", async () => {
  await verifySocialPreviews();
});
test("missing metadata, duplicate identities, SVG images, private canaries and corrupt assets are rejected", async () => {
  const html = await readFile(new URL("../public/index.html", import.meta.url), "utf8");
  for (const changed of [
    html.replace(/<meta property="og:title"[^>]*>/, ""),
    html.replace('</head>', '<meta property="og:url" content="https://poststeward.com/private">\n</head>'),
    html.replaceAll('/social/poststeward-v2.png', '/og-image.svg'),
    html.replace('content="en_GB"', 'content="en_GB" data-secret="PRIVATE_PREVIEW_SENTINEL"'),
    html.replace('href="https://poststeward.com/"', 'href="https://poststeward.com/?access_token=private"'),
  ]) assert.throws(() => verifyPage(changed, pages[0]));
  assert.throws(() => verifyPng(Buffer.from('This is an HTML error, not a PNG')));
});
test("live verifier refuses login redirects, missing/corrupt images and foreign legacy redirects", async () => {
  const png = await readFile(new URL("../public/social/poststeward-v2.png", import.meta.url));
  const send = overrides => async url => {
    if (new URL(url).protocol === "http:") return new Response(null, {status:301,headers:{Location:"https://poststeward.com/"}});
    const path = new URL(url).pathname;
    if (path === "/social/poststeward-v2.png") return overrides.image || new Response(png, {headers:{"Content-Type":"image/png"}});
    if (path.endsWith(".svg")) return new Response(null, {status:301,headers:{Location:overrides.location || "/social/poststeward-v2.png"}});
    const page = pages.find(page => page.path === path);
    return overrides.page || new Response(await readFile(new URL("../public/" + page.file, import.meta.url)), {headers:{"Content-Type":"text/html"}});
  };
  await verifySocialOrigin("https://poststeward.com", send({}));
  for (const overrides of [
    {page:new Response(null,{status:302,headers:{Location:"/auth/login"}})},
    {image:new Response("not found",{status:404})},
    {image:new Response("<html>challenge</html>",{headers:{"Content-Type":"text/html"}})},
    {location:"https://outside.example/private"},
  ]) await assert.rejects(verifySocialOrigin("https://poststeward.com", send(overrides)));
});
