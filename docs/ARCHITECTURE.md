# Public launch architecture

## Purpose

This repository hosts the public PostSteward launch experience. It explains the product accurately, demonstrates the agent operating model and provides a hardened path to `poststeward.com` without publishing the private product implementation.

## Product model

PostSteward is agent-native continuous GTM for builders.

The developer remains in the build. An agent works from project and GTM context it already has access to, selects a grounded story and uses PostSteward as the publishing execution lane. Over time, the product story, engagement and pipeline can accumulate before launch.

The public narrative therefore leads with the builder outcome. Scoped authority, deterministic effects and receipts explain why the agent lane can be trusted, but they are supporting architecture rather than the headline category.

## Public runtime

The launch site is deliberately dependency-light:

- static HTML/CSS/JavaScript;
- no client-side network requests in the interactive demo;
- Cloudflare Workers Static Assets;
- apex and `www` Custom Domains;
- strict edge security headers;
- machine-readable `product.json`, `agents.txt` and `llms.txt`.

The interactive command centre uses synthetic launch data and cannot publish anything.

## Source boundary

No private implementation source, implementation-repository location, provider credential or customer data belongs in this repository.

CI enforces this as a deployment invariant. The verifier rejects known private-source identifiers, the former evidence-led launch structure, private staging origins and common provider-authority/secret patterns.

## Agent-facing story

The public launch highlights three runtime interfaces:

1. CLI for local and coding agents.
2. HTTP for programmatic agent runtimes.
3. WebMCP for supported browser agents.

The strategy/context layer is intentionally decoupled. A GTM plan may live in connected documents, source vaults, project notes or the agent's existing working context. PostSteward is the execution lane, not a requirement to relocate that context.
