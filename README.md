# PostSteward launch surface

**PostSteward is agent-native continuous GTM for builders.**

Keep building. Let your agent keep building the market.

This repository hosts the public launch experience for `poststeward.com`: the Product Hunt story, an effect-free interactive command-centre demo, machine-readable product metadata and the Cloudflare deployment acceptance checks.

## The problem

Developers and technical founders often have to choose between two bad modes:

- stay in the build and let the market go quiet; or
- stop development repeatedly to reconstruct context, create content and publish it.

That creates a cold-launch problem. By the time the product is ready, the audience, conversations and pipeline are only just starting.

PostSteward lets the agent already working with project and GTM context keep the story moving while development continues.

## Agent-native interfaces

The product is designed for agents as runtime users, with humans remaining the operator and beneficiary:

- **CLI** for coding agents and local operator workflows;
- **HTTP** for programmatic agent runtimes;
- **WebMCP** for supported browser agents.

The public demo makes no provider calls. It exists to explain the operating model without requiring account access.

## Public/private boundary

This repository is a launch and presentation surface. It intentionally does **not** contain or link to private product implementation source, provider credentials, customer data, production authority or internal evidence repositories.

Public claims are constrained to behaviour visible in this repository and hosted deployment acceptance.

## Local verification

```bash
npm run verify
node --check public/app.js
node --check scripts/smoke-deployment.mjs
```

Local preview:

```bash
npm run dev
```

## Deployment

Production is served from Cloudflare Workers Static Assets on:

- `https://poststeward.com`
- `https://www.poststeward.com`

`main` deploys the custom-domain configuration after verification. The workflow then exercises both production hostnames and checks the product markers, security headers, public product metadata and public/private source boundary.

The only protected deployment value is the dedicated GitHub environment secret `CLOUDFLARE_API_TOKEN`.

See `docs/CLOUDFLARE_DEPLOYMENT.md` for the deployment contract and `launch/PRODUCT_HUNT.md` for the launch package.
