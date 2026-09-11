# Public launch architecture

## Purpose

This repository hosts the public PostSteward launch and documentation surface without publishing the private implementation.

The design goal is **agent-surface parity**: preserve the actual agent-first service UI and contract, then replace only unavailable public effects with clearly marked showcase states.

## Product model

PostSteward is social publishing infrastructure whose runtime user is an AI agent.

An authorised agent can operate through:

1. remote MCP;
2. plain HTTP operations;
3. CLI shell/cURL over the HTTP surface;
4. browser WebMCP on a connected workspace.

The builder problem explains why the product exists: the agent can keep the product story, engagement and GTM pipeline moving while the developer stays in development. It does not replace the product's agent-first interface with a human marketing dashboard.

## Public surfaces

The showcase mirrors the production information architecture:

- service landing page;
- four-step onboarding;
- full agent manual;
- workspace structure: connections, projects, exact campaigns, receipts, agent grants and Advanced automation;
- machine-readable discovery and operation metadata.

The workspace uses synthetic records and all action controls are non-effectful.

## One agent contract

The public agent guide and machine-readable artefacts describe the same current 26-operation catalogue:

- `agent-guide.md`
- `agents.txt`
- `llms.txt`
- `mcp.json`
- `help.json`
- `openapi.json`
- `docs/operations.md`

CI verifies the count and every operation name so the public showcase cannot silently drift into a weaker or stale contract.

## Showcase safety boundary

The browser JavaScript is deliberately fetch-free. The public site:

- never accepts provider credentials;
- never mints an agent token;
- never invokes a provider or private PostSteward service;
- never creates checkout or payment state;
- uses `<POSTSTEWARD_SERVICE_ORIGIN>` in executable examples;
- labels the workspace synthetic and non-effectful.

## Hosting

The launch site remains dependency-light static HTML/CSS/JavaScript on Cloudflare Workers Static Assets. Apex and `www` are Custom Domains, protected by the existing security headers and dual-host hosted verification.

## Source boundary

No private implementation repository identifier, private UI-source identifier, private staging/service origin, provider credential or customer data belongs in this repository. Verification fails if any of those patterns return.
