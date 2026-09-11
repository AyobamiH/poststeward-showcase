# PostSteward Showcase

Public launch, demonstration and acquisition surface for [PostSteward](https://github.com/AyobamiH/poststeward).

> **Architecture rule:** `AyobamiH/poststeward` is the canonical product. This repository is the stage, not a fork, rewrite, scheduler or second implementation.

## What this repository contains

- a high-craft static launch site;
- a deliberately non-effectful five-step publication walkthrough;
- versioned product evidence tied to canonical GitHub receipts;
- Product Hunt and OpenAI Developer Showcase preparation;
- a CI guard that rejects provider credentials/write logic and unsupported verified claims;
- Cloudflare Static Assets configuration and restrictive browser security headers.

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
- [Product Hunt pack](launch/PRODUCT_HUNT.md)
- [OpenAI Showcase pack](launch/OPENAI_SHOWCASE.md)
- [Security policy](SECURITY.md)

## Deployment

`wrangler.jsonc` defines an assets-only Cloudflare deployment named `poststeward-showcase`. Supply Cloudflare credentials and the eventual public domain outside this repository. Do not add secrets to git.
