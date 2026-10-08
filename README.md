# PostSteward public launch surface

**PostSteward is social publishing infrastructure built for AI agents.**

Its runtime user is the agent. The developer or technical founder remains the operator and beneficiary.

The product exists because builders should not have to stop development every time they need to tell the market what changed. An authorised agent can keep the product story, social engagement and GTM pipeline moving through PostSteward while the builder stays in the build.

## What agents get

The public launch surface preserves the actual agent contract:

- **Remote MCP** with a scoped Bearer token;
- **HTTP operations** with the same named catalogue;
- **CLI via HTTP** for shell/cURL and coding-agent workflows;
- **browser WebMCP** on a real connected workspace;
- explicit project-to-account routing;
- immutable exact campaign copy;
- publish-now and explicit schedules;
- durable delivery receipts and provider readback states;
- scoped agent grants;
- Advanced continuing operation for reviewed source monitoring and spaced allocation.

The agent guide, Markdown guide, `agents.txt`, `llms.txt`, `mcp.json`, help metadata, OpenAPI and operation reference describe one 50-operation contract.

## Production entry points and optional demo

`poststeward.com` is the public product and installation website. Its primary buttons lead to Google sign-in at `https://app.poststeward.com/auth/login`; owner approval, OAuth, agent tokens and publishing happen in that authenticated application.

Homepage and onboarding copy describe the real product. Executable HTML examples use `https://app.poststeward.com`. The homepage links to the live application operation reference and help for the complete runtime catalogue; legacy static machine files remain documentation-only.

The optional workspace demo at `/workspace/` uses sample records and inert controls and directs users to sign in for real work. It is not the primary workspace journey. Advanced is shown as coming soon.

## Public routes

- `/` — service overview and agent transports
- `/onboarding/` — four-step setup flow
- `/agent-guide/` — complete human-readable agent manual
- `/workspace/` — non-effectful workspace preview
- `/agent-guide.md` — Markdown manual
- `/agents.txt` — autonomous-caller rules
- `/llms.txt` — LLM discovery index
- `/mcp.json` — transport and 50-operation metadata
- `/help.json` — machine-readable help summary
- `/openapi.json` — generic HTTP operation contract
- `/docs/operations.md` — operation reference

## Public/private boundary

This repository contains the launch surface and canonical public runtime distribution. Its release artifacts may reference the exact publicly released runtime archive. Other pages must not contain or link to private product implementation source, private UI-source locations, provider credentials, customer data or private service origins.

CI rejects those identifiers and also rejects drift in the agent UI, machine-readable operation catalogue or showcase safety boundary.

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

Production is served by Cloudflare Workers Static Assets at:

- `https://poststeward.com`
- `https://www.poststeward.com`

Every `main` deployment verifies both hostnames, security headers, the homepage, onboarding, agent guide, workspace preview and machine-readable agent contract.

## Runtime distribution

The deploy workflow prepares `/install.sh` and `/releases/stable.json` and `/releases/beta.json` from verified deployed releases. The installer is compared byte-for-byte with its immutable GitHub source and the deployed application asset. Stable metadata must match the live production health revision. Missing, stale or mismatched metadata blocks deployment.

The branded domain distributes installation artifacts; pairing and cloud coordination target the authenticated application domain. Public preview controls remain inert. `scripts/sync-runtime-release.mjs` is build-time tooling; browser JavaScript stays fetch-free.
