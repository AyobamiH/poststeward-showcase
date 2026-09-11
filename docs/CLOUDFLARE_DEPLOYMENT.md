# Cloudflare deployment

## Purpose

Deploy the public showcase without sharing runtime authority with canonical `AyobamiH/poststeward`.

The canonical repository established the proven conventions reused here: Node 24, a protected Cloudflare API token, telemetry disabled in CI, pinned Wrangler tooling and post-deployment verification. The showcase deliberately does **not** reuse PostSteward's D1, Durable Objects, OAuth secrets, billing secrets or application deployment workflow.

## Cloudflare topology

### Production Custom Domains

`poststeward.com` has now been purchased in Cloudflare. `wrangler.domain.jsonc` is therefore the normal `main`-branch deployment target and attaches:

- `poststeward.com`;
- `www.poststeward.com`.

Both are Cloudflare **Custom Domains**, not Workers Routes. PostSteward Showcase is the origin, so Cloudflare creates and manages the required DNS records and certificates. The production configuration disables both `workers.dev` and preview URLs so the launch has one public origin family.

The homepage declares `https://poststeward.com/` as canonical even while `www` is attached.

### Diagnostic Workers origin

`wrangler.jsonc` retains `https://poststeward-showcase.woeinvests.workers.dev` only as an explicit diagnostic/recovery target. Ordinary pushes to `main` do not choose it. It can be selected manually through workflow dispatch if production-domain diagnosis requires an origin independent of Custom Domain attachment.

## Cloudflare account

The non-secret Cloudflare account ID was recovered from canonical PostSteward's redacted staging inspection and is pinned in the showcase workflow:

`6ddcbcb8474f1a7e460b2f0aabec0e2f`

That inspection kept the API token masked. The showcase therefore does not require a duplicate GitHub variable for the account identifier.

## GitHub environment

The deployment job uses a GitHub environment named `showcase`.

Configure only one protected value:

- environment secret `CLOUDFLARE_API_TOKEN` — a dedicated deploy token for this public showcase.

Do **not** copy the canonical PostSteward token merely for convenience. Do not paste the token into source files, issues, workflow logs or chat.

## API token scope

Prefer a dedicated token for this public showcase rather than copying the canonical PostSteward deployment token. Start from Cloudflare's **Edit Cloudflare Workers** token template and scope resources down to account `6ddcbcb8474f1a7e460b2f0aabec0e2f` and the `poststeward.com` zone.

The token needs only the Worker script/custom-domain capabilities Wrangler requires. Do not grant D1, R2, KV, billing or unrelated account administration solely for this showcase.

## Workflow behaviour

`.github/workflows/deploy.yml` runs verification first. The deployment job then:

1. refuses to deploy outside `AyobamiH/poststeward-showcase` `main`;
2. uses the pinned non-secret Cloudflare account ID;
3. checks whether the dedicated API token is present;
4. skips effectfully, but successfully, when that secret is absent;
5. targets `poststeward.com` on ordinary `main` pushes;
6. retains `workers.dev` only as an explicit manual diagnostic target;
7. deploys with exactly Wrangler `4.130.0`, matching the canonical PostSteward release tooling;
8. runs bounded HTTPS smoke verification against the selected origin.

The smoke check requires the expected showcase HTML, versioned evidence and security headers. Custom-domain certificate/DNS convergence can retry for up to two minutes; a deployment upload is not treated as acceptance until the hosted checks pass.

## Domain activation sequence

1. `poststeward.com` is purchased in the Cloudflare account.
2. Confirm the zone is active and there is no conflicting origin record for the apex or `www`.
3. Save the dedicated `CLOUDFLARE_API_TOKEN` secret in the GitHub `showcase` environment.
4. Merge a deployment-relevant change to `main` (or explicitly dispatch `custom-domain`).
5. Require the hosted smoke job to pass on `https://poststeward.com`.
6. Independently verify `https://www.poststeward.com` resolves through the same Cloudflare Custom Domain family.
7. Use `https://poststeward.com` for Product Hunt and OpenAI Developer Showcase submissions.

## Boundary

Deploying this repository must never mutate `AyobamiH/poststeward`, its Worker, D1 database, Durable Objects, OAuth applications or provider credentials. The only shared infrastructure assumption is the Cloudflare account/Workers namespace.
