# OpenAI Showcase pack

## Title

**PostSteward — social publishing infrastructure for AI agents**

## Description

PostSteward gives an AI agent a scoped, inspectable path to social publishing. The same named operation catalogue is reachable over remote MCP and HTTP, shell/cURL uses the HTTP surface, and a connected browser workspace can expose those scoped operations through WebMCP. The agent resolves explicit destinations, stores exact copy, publishes or schedules once and reads a durable receipt for the actual provider outcome.

The product grew from a builder problem: a developer should not have to leave development every time the product story needs to move. PostSteward lets the agent keep social engagement and the GTM pipeline warm while the builder stays in the build.

## Agent-native surfaces

The launch experience preserves the actual agent-facing information architecture:

- service overview;
- four-step agent onboarding;
- workspace preview;
- full 26-operation catalogue;
- scopes and consequence annotations;
- receipt states and retry rules;
- `agent-guide.md`, `agents.txt`, `llms.txt`, `mcp.json`, OpenAPI and machine help.

## Trust model

- scoped tokens rather than provider credentials;
- explicit project/account routing;
- immutable exact campaign copy;
- one idempotency key per consequence;
- receipt-first outcome inspection;
- no blind retry after an ambiguous external effect;
- source content treated as untrusted data under continuing operation.

## Showcase boundary

The public launch site is non-effectful. It does not accept provider credentials, issue live agent tokens, create payments or send posts. Usage examples use a service-origin placeholder until public effectful access is opened.

## Model attribution rule

Only attribute work to a named OpenAI model when the exact contribution is supported by development-session or submission evidence. Do not describe the entire product as built by a model merely because that model helped with development review, launch positioning or showcase preparation.

## Submission visuals

Use the real terminal UI and agent routes: overview, transports, onboarding, workspace, operation catalogue and receipt semantics. Do not replace the agent interface with a generic marketing dashboard.
