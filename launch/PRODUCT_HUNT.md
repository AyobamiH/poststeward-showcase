# Product Hunt launch pack

Source guidance checked 11 September 2026: Product Hunt recommends a direct product URL, a tagline up to 60 characters, description up to 500 characters, square thumbnail (recommended 240×240), at least two gallery images (recommended 1270×760), and an optional YouTube demo. The product should be live/usable for the strongest featuring case.

## Core listing

**Name**

PostSteward

**Tagline**

Accountable social publishing for AI agents

**Description**

PostSteward gives AI agents a controlled path to social publishing without handing them unchecked account authority. Agents can prepare exact content and destinations; owners review the effect before it happens; publication state is durable; uncertain writes are not blindly retried; and provider readback turns “the API said OK” into inspectable evidence.

**Suggested launch tags**

- AI Agents
- Social Media
- Developer Tools

**Pricing at launch**

Use the status that is actually public on launch day. Do not advertise paid Advanced until canonical payment acceptance and public charging are approved.

## Gallery storyboard

Do not manufacture a real-provider success state. Capture these after the canonical live acceptance receipt exists.

1. **Hero — the promise**: “Give the agent a publishing lane. Not the keys to the building.” Include the five-control flow.
2. **Exact owner review**: real canonical UI showing selected provider/account, immutable destination and exact text before approval. Redact private identifiers.
3. **Verified receipt**: real publication receipt/readback state showing that provider verification is distinct from dispatch.
4. **Architecture/evidence**: showcase evidence panel with canonical revision and live receipt link.

## Demo video — 60–90 seconds

0–10s: Show the problem: an agent wants to publish under a real account.

10–25s: Agent prepares destination + exact content. Emphasise that this is intent, not authority.

25–40s: Owner reviews the frozen effect and approves it. Show the cancellation boundary.

40–60s: Canonical PostSteward dispatches one durable write. Do not cut around retries or uncertainty.

60–75s: Separate provider readback proves what is actually live. Open the receipt.

75–90s: End on the evidence panel and invite feedback on the approval/readback model.

## Maker first comment

Hey Product Hunt — I built PostSteward because “give the agent a social API token and hope for the best” stopped feeling like an acceptable architecture.

The product separates agent intent from account authority. An agent can prepare a post, but the owner sees the exact destination and exact copy before the effect is authorised. PostSteward then keeps durable publication state, avoids blind retries after uncertain writes, and independently reads the resulting provider object back where the platform supports it.

The part I care about most is not automatic posting. It is making external effects inspectable: what did the agent ask for, what did I approve, what was attempted, and what can we actually verify afterwards?

I’d especially value feedback from people building agents that operate real customer accounts: where would you draw the approval boundary, and which external effects still make you uncomfortable delegating?

## Launch integrity

Ask people to visit, test and comment — not to upvote. Product Hunt explicitly treats authentic engagement as important and prohibits vote manipulation.
