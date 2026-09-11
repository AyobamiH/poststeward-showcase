# Cloudflare deployment contract

## Production target

The normal production target is the Cloudflare Worker `poststeward-showcase` serving Static Assets on two Custom Domains:

- `poststeward.com`
- `www.poststeward.com`

`wrangler.domain.jsonc` is the production configuration. It disables `workers.dev` and preview URLs and attaches both hostnames as Custom Domains.

`wrangler.jsonc` exists only as a manually selected diagnostic/recovery target on the account's `workers.dev` subdomain.

## Authentication

The Cloudflare account ID is a non-secret identifier pinned in the deployment workflow. Authentication uses one protected GitHub environment secret:

`CLOUDFLARE_API_TOKEN`

Use a dedicated, least-privilege token for this launch Worker. Do not reuse unrelated product credentials and do not commit the token.

## CI behaviour

On a deployment-relevant push to `main`:

1. checkout uses a pinned action SHA with persisted Git credentials disabled;
2. Node 24 runs the repository verifier;
3. browser JavaScript and the hosted smoke verifier receive syntax checks;
4. exact Wrangler `4.130.0` deploys `wrangler.domain.jsonc`;
5. hosted acceptance independently exercises both production hostnames.

Hosted acceptance requires:

- HTTPS success;
- the current continuous-GTM product markers;
- canonical metadata pointing at the apex;
- `product.json` with CLI, HTTP and WebMCP interfaces;
- HSTS, CSP, X-Content-Type-Options, Referrer-Policy, X-Frame-Options, COOP, CORP and Permissions-Policy;
- no private implementation-repository identifier in the rendered page.

## Failure policy

A missing token produces a safe no-op rather than an unauthenticated deploy attempt. A configured token that cannot deploy is a real failure and should be diagnosed at the failing Cloudflare layer.

Workers.dev can be selected manually only for diagnostic isolation. It is not the Product Hunt origin.
