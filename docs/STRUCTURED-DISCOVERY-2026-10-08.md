# PostSteward apex structured discovery — 2026-10-08

The public showcase (`poststeward.com` and `www`) is hosted by `AyobamiH/poststeward-showcase`, via the separate Cloudflare Worker `poststeward-showcase` using `wrangler.domain.jsonc`. The authenticated application uses `app.poststeward.com` and remains independent.

The marketing root publishes Organization, WebSite and SoftwareApplication JSON-LD with linked stable `@id` identities. The Organization logo URL is `https://poststeward.com/icon-512.png`, a 512×512 copy of the existing reviewed application identity asset. The existing OG/social card remains separate and unchanged.

No offers, product price, customer ratings, claimed agent payments or account capability are inferred by the metadata. Public discovery documents and installer distributions retain their own source-of-truth and security tests.

Release gates: `npm run verify`, `node --test tests/*.test.mjs`, GitHub `Verify showcase` green, dedicated `Deploy showcase` workflow success on `main` and outside-in HTTPS readback of root JSON-LD and logo, both domains, install distribution and public machine surfaces. Confirm that `app.poststeward.com/readiness.json` still reports its exact accepted release after showcase deployment.
