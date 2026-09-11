# Showcase architecture

## Purpose

This repository is a presentation boundary around the canonical PostSteward product. It exists so launch work can move quickly without changing the product roadmap or creating a second implementation.

```text
Product Hunt / OpenAI Showcase / visitors
                    |
                    v
        poststeward-showcase
     story + evidence + walkthrough
                    |
      links / explicit hand-off only
                    |
                    v
          AyobamiH/poststeward
 auth + authority + state + publication
      + recovery + billing + readback
```

## Runtime

The v1 showcase is static HTML, CSS and browser JavaScript with no runtime package dependencies. It can be deployed through Cloudflare Static Assets.

The browser JavaScript performs one same-origin read of `evidence.json`. It does not call social providers, Stripe, Google, GitHub APIs or canonical PostSteward mutation endpoints.

## Trust boundary

The showcase can link to canonical product surfaces, but all effectful work remains there. There is no credential input, OAuth callback, social provider adapter, billing route, durable store or agent token in this repository.

A repository verifier enforces this boundary with fail-closed pattern checks and requires verified claims to point at evidence in `AyobamiH/poststeward`.

## Evidence model

`public/evidence.json` is the versioned public claim set. Each fact has:

- an ID;
- a human-readable label and value;
- `verified` or `open` state;
- a canonical evidence URL.

An open gate stays open until the canonical product produces real external evidence. The showcase does not infer completion from implemented code, passing fixtures or deployed configuration.

## Deployment

`wrangler.jsonc` defines a static-assets deployment named `poststeward-showcase`. Security headers are in `public/_headers`. Deployment credentials, domains and environment configuration must be supplied outside the repository.
