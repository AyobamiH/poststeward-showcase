# PostSteward Showcase

Public launch, demonstration and acquisition surface for [PostSteward](https://github.com/AyobamiH/poststeward).

## Boundary

`AyobamiH/poststeward` is the canonical product. This repository is deliberately **not** a fork, rewrite, scheduler or second implementation of PostSteward.

The showcase may:

- explain the product and its safety model;
- present evidence backed by the canonical repository and deployed service;
- provide an interactive, non-effectful walkthrough;
- link or hand off to canonical PostSteward owner/user journeys;
- contain launch assets and copy for Product Hunt and the OpenAI Developer Showcase.

The showcase must not:

- contain social-provider credentials or provider write logic;
- reproduce PostSteward authentication, billing, recovery or durable state;
- claim an external acceptance gate has passed without evidence;
- mutate the canonical PostSteward repository as part of showcase deployment;
- silently turn simulated walkthrough UI into a real publication path.

Real publication and account authority remain inside the canonical PostSteward service.

## Status

Initial showcase implementation is being prepared on a feature branch. Product facts and evidence are versioned in `src/data/evidence.ts`; launch claims must be traceable to those records.
