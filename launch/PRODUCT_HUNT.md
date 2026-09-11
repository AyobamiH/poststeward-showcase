# Product Hunt launch pack

## Name

PostSteward

## Tagline

**Social publishing your AI agent can prove**

## Description

PostSteward gives AI agents a controlled publishing lane to X, Threads and LinkedIn. An agent can work through remote MCP, plain HTTP, CLI shell calls or browser WebMCP, resolve explicit project/account routes, submit exact copy, publish or schedule it, then inspect a durable receipt instead of guessing what happened.

I built it from a developer problem: when I stayed heads-down shipping, market-building went quiet; when I stopped to turn every build milestone into content, development flow broke. PostSteward lets the agent keep the product story, social engagement and GTM pipeline moving while the builder stays in the build.

The public launch site is currently a non-effectful showcase of the agent UI and full operation contract. It does not accept provider credentials or create live posts until public effectful access is opened.

## Suggested topics

- AI Agents
- Developer Tools
- Social Media

## First comment

I built PostSteward after repeatedly hitting the same trade-off: either keep developing and go quiet, or stop the build to turn the work into posts.

The bigger cost appears later. If you only start telling the product story when the product is ready, launch day is also day one for recognition, conversations and pipeline.

PostSteward is built for the agent already working alongside you. Give that agent scoped publishing authority and it can use remote MCP, HTTP, shell/cURL or browser WebMCP to submit exact project updates, schedule them and read durable receipts while you stay in development.

What I care about technically is that the agent never has to guess: destinations are explicit, campaign copy is immutable, mutations use idempotency keys, and an uncertain provider effect is not blindly retried.

For this launch, the public site exposes the complete agent manual and a synthetic workspace, but deliberately does not accept credentials or execute posts yet.

I would especially value feedback from developers and agent operators on the operation catalogue and the point where you would be comfortable giving an agent continuing publishing authority.

## Gallery storyboard

1. **Service overview** — the actual terminal UI: “Let an agent post to X, Threads and LinkedIn — and prove what it did.”
2. **Agent access paths** — remote MCP, HTTP/CLI and WebMCP snippets.
3. **Onboarding** — connect account → bind project → issue scoped token → publish/read receipt.
4. **Workspace** — connections, project routing, exact campaign, receipts and agent scopes.
5. **Agent manual** — operation catalogue, receipt states and no-blind-retry rule.
6. **Advanced** — reviewed source monitoring and spaced continuing operation, clearly shown as $5/workspace/month.

Synthetic workspace records must remain visibly labelled synthetic.

## 60–90 second demo

**0–10s**: Show the terminal service overview and say: “PostSteward is a publishing lane for AI agents.”

**10–25s**: Show the three execution paths: remote MCP, HTTP/CLI and browser WebMCP.

**25–42s**: Walk the four onboarding steps and explain scoped token + explicit routing.

**42–62s**: Show the synthetic workspace: exact copy, publish/schedule boundary and receipt states.

**62–78s**: Open the agent manual and show operation effects, idempotency and `ambiguous_effect` handling.

**78–90s**: Explain the founder outcome: the agent keeps the story and pipeline moving while you keep building.

## Pricing copy

**Free** — agent publishing, explicit schedules, routing, receipts, on-demand metrics and all agent transports.

**Advanced — $5/workspace/month** — reviewed source monitoring, replenishment, rolling allocation, spacing controls and scheduled metrics.

Until public billing acceptance is complete, do not present an active purchase button.
