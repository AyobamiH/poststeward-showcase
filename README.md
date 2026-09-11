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

The agent guide, Markdown guide, `agents.txt`, `llms.txt`, `mcp.json`, help metadata, OpenAPI and operation reference describe one 26-operation contract.

## Showcase boundary

`poststeward.com` is the public Product Hunt / showcase surface. It deliberately does **not** accept provider credentials, issue live agent tokens, create payments or execute social posts.

Where the real product has an effectful capability, the showcase preserves its UI and usage documentation but labels the action as preview-only. Examples use `<POSTSTEWARD_SERVICE_ORIGIN>` rather than exposing a private service origin.

The synthetic workspace at `/workspace/` mirrors the operator panels without creating external effects.

## Public routes

- `/` — service overview and agent transports
- `/onboarding/` — four-step setup flow
- `/agent-guide/` — complete human-readable agent manual
- `/workspace/` — non-effectful workspace preview
- `/agent-guide.md` — Markdown manual
- `/agents.txt` — autonomous-caller rules
- `/llms.txt` — LLM discovery index
- `/mcp.json` — transport and 26-operation metadata
- `/help.json` — machine-readable help summary
- `/openapi.json` — generic HTTP operation contract
- `/docs/operations.md` — operation reference

## Public/private boundary

This repository contains only the launch surface. It must not contain or link to private product implementation source, private UI-source locations, provider credentials, customer data or private service origins.

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
