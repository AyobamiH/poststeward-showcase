# Launch plan

## Objective

Prepare PostSteward for public discovery without changing the canonical `AyobamiH/poststeward` roadmap.

## Critical path

### Gate A — showcase foundation

- [x] Separate repository and explicit architecture boundary.
- [x] Public landing page and non-effectful interactive walkthrough.
- [x] Versioned evidence panel tied to canonical receipts.
- [x] Product Hunt and OpenAI Showcase preparation files.
- [x] CI boundary verification and static security headers.

### Gate B — canonical live proof

Must happen in `AyobamiH/poststeward`, not here:

- [ ] Complete a real owner Threads grant.
- [ ] Verify stable provider identity.
- [ ] Prepare exact destination and text.
- [ ] Approve one immutable review.
- [ ] Observe the cancellation boundary.
- [ ] Complete one durable provider publication.
- [ ] Independently read back the resulting post.
- [ ] Record the canonical acceptance receipt.

Only after the receipt exists may `public/evidence.json` move `live-publication` from `open` to `verified`.

### Gate C — public availability

- [ ] Deploy the showcase to a stable public origin.
- [ ] Decide the public PostSteward user entry point; do not expose an owner-only staging journey as a general signup path.
- [ ] Verify desktop/mobile rendering, social cards and external links on the deployed origin.
- [ ] Record the public URL in Product Hunt/OpenAI submission drafts.

### Gate D — launch packaging

Product Hunt currently expects a direct product URL, a <=60 character tagline, <=500 character description, square thumbnail and at least two gallery images. A video is optional. Launch copy is prepared in `launch/PRODUCT_HUNT.md`; visual capture happens after Gate B so gallery frames can show real evidence.

For OpenAI Developer Showcase, keep model attribution evidence-backed. Do not claim GPT-6 Astra built or powered a flow unless the relevant development/session provenance supports that statement.

## Definition of launch-ready

Launch-ready means all of the following are true at the same time:

1. the showcase is publicly reachable and high-craft;
2. the canonical live Threads publish/readback receipt exists;
3. every headline claim maps to evidence;
4. a new visitor can understand the product in under one minute;
5. the Product Hunt gallery/demo shows the real effect path, not fabricated provider success;
6. launch does not require a commit to the canonical product solely for marketing presentation.
