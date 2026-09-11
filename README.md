# PostSteward Showcase

Public launch, demonstration and acquisition surface for [PostSteward](https://github.com/AyobamiH/poststeward).

> **Architecture rule:** `AyobamiH/poststeward` is the canonical product. This repository is the stage, not a fork, rewrite, scheduler or second implementation.

## What this repository contains

- a high-craft static launch site;
- a deliberately non-effectful five-step publication walkthrough;
- versioned product evidence tied to canonical GitHub receipts;
- Product Hunt and OpenAI Developer Showcase preparation;
- a CI guard that rejects provider credentials/write logic and unsupported verified claims;
- Cloudflare Static Assets configuration and restrictive browser security headers;
- an isolated Cloudflare deployment path for `poststeward.com`.

## What it must never contain

- social-provider credentials or provider write logic;
- PostSteward authentication, billing, recovery or durable product state;
- a fabricated provider success state;
- a claim that an external acceptance gate passed without a canonical receipt;
- deployment logic that mutates `AyobamiH/poststeward`.

Real publication and account authority remain inside canonical PostSteward.

## Local preview

No dependency install is required for the site or verifier.

```bash
npm run verify
npm run dev
```

Open `http://localhost:4173`.

## Evidence

`public/evidence.json` is the public claim ledger. The initial showcase candidate is pinned to canonical revision `e8a95086548a23541e89e2f33d56c0abd274d9cc` and intentionally leaves the controlled real Threads publication/readback gate open.

Update an `open` gate to `verified` only after the canonical repository has a real evidence URL.

## Launch work

- [Launch plan](docs/LAUNCH_PLAN.md)
- [Architecture boundary](docs/ARCHITECTURE.md)
- [Cloudflare deployment](docs/CLOUDFLARE_DEPLOYMENT.md)
- [Product Hunt pack](launch/PRODUCT_HUNT.md)
- [OpenAI Showcase pack](launch/OPENAI_SHOWCASE.md)
- [Security policy](SECURITY.md)

## Deployment

The showcase uses the same release-tooling discipline proven in canonical PostSteward without sharing application state or product secrets.

- `poststeward.com` has been purchased and is now the normal production deployment target.
- `wrangler.domain.jsonc` attaches `poststeward.com` and `www.poststeward.com` as Cloudflare Custom Domains and disables alternate `workers.dev`/preview origins.
- `wrangler.jsonc` retains `poststeward-showcase.woeinvests.workers.dev` only as a manually selected diagnostic target.
- `.github/workflows/deploy.yml` verifies first, uses the recovered non-secret Cloudflare account ID, requires only a dedicated `CLOUDFLARE_API_TOKEN` secret in the protected `showcase` environment, pins Wrangler `4.130.0`, and performs bounded hosted smoke checks after deployment.
- `https://poststeward.com/` is the canonical public URL in page metadata, sitemap and launch material.

Cloudflare credentials stay outside git. See [Cloudflare deployment](docs/CLOUDFLARE_DEPLOYMENT.md) for the exact environment contract and activation sequence.
