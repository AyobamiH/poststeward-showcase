# Security boundary

This repository is intentionally a non-effectful public launch surface.

It must never contain:

- social-provider credentials or refresh tokens;
- customer or operator session data;
- billing secrets;
- private implementation source or links that disclose its repository location;
- effectful provider adapters;
- production account identifiers that are not intended to be public.

The browser demo is synthetic and must make no network call from `public/app.js`.

Deployment authentication is isolated to the GitHub `showcase` environment secret `CLOUDFLARE_API_TOKEN`. The token value must never be committed, printed or pasted into public issues.

CI scans the public tree for private-source identifiers and common credential/provider-authority patterns before deployment.
