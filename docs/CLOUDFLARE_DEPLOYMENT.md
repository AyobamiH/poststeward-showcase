# Cloudflare deployment

## Purpose

Deploy the public showcase without sharing runtime authority with canonical `AyobamiH/poststeward`.

The canonical repository established the proven conventions reused here: Node 24, a protected Cloudflare API token, an account ID supplied outside source control, telemetry disabled in CI, pinned Wrangler tooling and post-deployment verification. The showcase deliberately does **not** reuse PostSteward's D1, Durable Objects, OAuth secrets, billing secrets or application deployment workflow.

## Cloudflare topology

### Phase 1 — Workers development origin

`wrangler.jsonc` deploys the static site as Worker `poststeward-showcase` with:

- Workers Static Assets from `./public`;
- `workers_dev: true`;
- preview URLs disabled;
- no production domain attachment.

Expected origin for the existing Cloudflare account:

`https://poststeward-showcase.woeinvests.workers.dev`

### Phase 2 — production Custom Domains

After `poststeward.com` is active in the same Cloudflare account, `wrangler.domain.jsonc` attaches:

- `poststeward.com`;
- `www.poststeward.com`.

Both are Cloudflare **Custom Domains**, not Workers Routes. PostSteward Showcase is the origin, so Cloudflare creates the required DNS records and certificates. The production configuration disables both `workers.dev` and preview URLs so the launch has one public origin family.

The homepage declares `https://poststeward.com/` as canonical even while `www` is attached.

## GitHub environment

The deployment job uses a GitHub environment named `showcase`.

Configure only:

- environment variable `CLOUDFLARE_ACCOUNT_ID` — the Cloudflare account containing the `woeinvests.workers.dev` namespace and the new domain;
- environment secret `CLOUDFLARE_API_TOKEN` — a dedicated deploy token;
- environment variable `CLOUDFLARE_CUSTOM_DOMAIN_ENABLED=true` only after the `poststeward.com` zone is active and ready to attach.

Do not paste any of these values into source files, issues, workflow logs or documentation.

## API token scope

Prefer a dedicated token for this public showcase rather than copying the canonical PostSteward deployment token. Start from Cloudflare's **Edit Cloudflare Workers** token template and scope resources down to the account used for this Worker and the `poststeward.com` zone when the zone exists.

The required capabilities are the Worker-script/domain capabilities used by Wrangler. Do not grant D1, R2, KV, billing or unrelated account administration solely for this showcase.

## Workflow behaviour

`.github/workflows/deploy.yml` runs verification first. The deployment job then:

1. refuses to deploy outside `AyobamiH/poststeward-showcase` `main`;
2. checks whether the account ID and API token are present;
3. skips effectfully, but successfully, when credentials are absent;
4. defaults to the `workers.dev` configuration;
5. selects the custom-domain configuration only through an explicit workflow-dispatch target or `CLOUDFLARE_CUSTOM_DOMAIN_ENABLED=true`;
6. deploys with exactly Wrangler `4.130.0`, matching the canonical PostSteward release tooling;
7. runs bounded HTTPS smoke verification against the selected origin.

The smoke check requires the expected showcase HTML, versioned evidence and security headers. Custom-domain certificate/DNS convergence can retry for up to two minutes; a deployment upload is not treated as acceptance until the hosted checks pass.

## Domain activation sequence

1. Purchase/add `poststeward.com` to the same Cloudflare account.
2. Confirm the zone is active.
3. Ensure neither `poststeward.com` nor `www.poststeward.com` has a conflicting CNAME intended for another origin.
4. Set `CLOUDFLARE_CUSTOM_DOMAIN_ENABLED=true` in the GitHub `showcase` environment.
5. Trigger the deploy workflow or merge a deployment-relevant change to `main`.
6. Require the hosted smoke job to pass on `https://poststeward.com`.
7. Use `https://poststeward.com` for Product Hunt and OpenAI Developer Showcase submissions.

## Boundary

Deploying this repository must never mutate `AyobamiH/poststeward`, its Worker, D1 database, Durable Objects, OAuth applications or provider credentials. The only shared infrastructure assumption is the Cloudflare account/Workers namespace.
