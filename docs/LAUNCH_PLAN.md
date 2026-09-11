# PostSteward launch plan

## Product category

**Agent-first social publishing infrastructure for builders.**

The runtime user is the AI agent. Product Hunt visitors are humans evaluating whether PostSteward gives their agents a reliable way to publish and keep GTM moving while they stay in the build.

## Launch promise

**Social publishing your AI agent can prove.**

Supporting outcome:

**Keep building while your agent keeps the product story and pipeline moving.**

## What the launch must show

The public experience should demonstrate the real information architecture, not invent a simplified marketing dashboard:

1. the agent service overview;
2. remote MCP, HTTP, CLI-via-HTTP and WebMCP paths;
3. four-step onboarding;
4. the full operation catalogue and safety rules;
5. workspace panels for connections, project binding, exact campaigns, receipts, agent access and Advanced automation;
6. machine-readable discovery for agents and LLMs.

Where effectful public access is not yet opened, preserve the UI and usage contract but mark the action preview-only.

## Why builders care

A developer who waits until release day to start telling the product story also starts recognition, conversations and pipeline from zero. PostSteward lets the agent already working alongside the builder keep that market-building activity moving without forcing the developer out of flow.

## Product Hunt critical path

Before submission:

- apex and `www` pass hosted acceptance;
- agent-first route parity passes CI;
- all 26 current operations are discoverable in the machine contract;
- synthetic workspace is clearly labelled and no control causes an external effect;
- public/private source boundary passes CI;
- Product Hunt raster assets and demo use the real agent-facing UI;
- billing and provider limitations are described accurately.

## Claim rules

Do not call shell/cURL a dedicated PostSteward CLI binary. Say **CLI via HTTP** unless a packaged CLI is released.

Do not claim that PostSteward owns a context system merely because an agent can access it. Project/GTM context can come from connected documents, repositories, notes or the agent's working context.

Do not fabricate engagement, lead, publication or customer counts. Synthetic records must be labelled synthetic.

Do not publish private implementation-source locations, UI-source locations, credentials or private service origins.
