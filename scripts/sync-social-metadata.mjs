import {readFile, writeFile} from "node:fs/promises";
import {pages, metadata} from "./social-previews.mjs";
for (const page of pages) {
  const file = new URL("../public/" + page.file, import.meta.url);
  const html = await readFile(file, "utf8");
  const head = html.match(/<head>[\s\S]*?<\/head>/i)[0];
  const clean = head.replace(/<title>[\s\S]*?<\/title>/gi, "")
    .replace(/<meta\b[^>]*(?:name="(?:description|twitter:[^"]+)"|property="og:[^"]+")[^>]*>/gi, "")
    .replace(/<link\b[^>]*rel="canonical"[^>]*>/gi, "")
    .replace(/<\/head>/i, metadata(page) + "\n</head>");
  await writeFile(file, html.replace(head, clean).replace(/[ \t]+$/gm, ""));
}
console.log("Wrote initial-HTML social metadata for " + pages.length + " routes.");
