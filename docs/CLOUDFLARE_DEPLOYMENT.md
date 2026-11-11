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

1. the repository-scoped, isolated `poststeward-showcase` runner accepts the trusted main job, then checkout uses a pinned action SHA with persisted Git credentials disabled;
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

A missing dedicated token fails the job before deployment; a skipped deployment is not accepted as a successful release. A configured token that cannot deploy is a real failure and should be diagnosed at the failing Cloudflare layer.

Workers.dev can be selected manually only for diagnostic isolation. It is not the Product Hunt origin.

## Self-hosted execution

The workflow keeps the existing GitHub Actions checks and the dedicated `showcase`
environment secret. Each job receives a fresh repository-scoped JIT runner in an
ephemeral container. The runner has no host mount, Docker socket, SSH agent or
user credential store. A separate network namespace rejects private and metadata
address ranges. The registration credential is piped into the container and is
not persisted to a file.

Trusted main jobs and owner-authored pull requests from this repository use the
`poststeward-showcase` label. Fork pull requests and other actors retain the hosted
runner path. They never enter the owner machine. The container is discarded after
each job, including between verification and environment-secret deployment.

The listener implementation is in `ops/actions-runner/`. It reuses the already
verified PostSteward Node 24 runner and egress images, pinned to their installed
image IDs. Its service, network, containers and repository registration are
separate from the product release and monitoring runners.

For an app release refresh, dispatch `Deploy showcase` on reviewed `main` with
`runtime_revision` equal to the accepted app production SHA and `target` equal
to `custom-domain`. The existing preparation script compares app health, stable
and beta manifests, immutable installer source and deployed installer bytes
before preparing assets. The subsequent verifier and both-hostname smoke checks
remain required. Routine main pushes retain their existing deployment behaviour.

## Automatic beta distribution reconciliation

`distribution-reconcile.yml` runs every three hours and can be dispatched manually. It checks
staging beta against both public hostnames **byte-for-byte** while requiring the public stable
manifest to match production and all four installers to match. A healthy staging deployment
alone does not authorise promotion: if beta differs, the job requires successful source PR
checks on the exact merged staging SHA, performs a clean isolated beta installation from the
staging channel (including the installer's runtime-tree digest verification, version and JSON
help smoke), and dispatches the existing `showcase`-environment-protected `deploy.yml`.
The dispatch pins both the accepted production stable SHA and the independently checked beta
SHA. If staging changes between preflight and deployment, preparation fails closed.

The reconciliation job waits for both public hosts to converge, then independently rechecks
stable, beta and installer bytes. A failed or incomplete run opens or updates the persistent
GitHub issue **Distribution reconciliation failed**; only confirmed convergence closes it.
No failed source checks are waived, no production stable promotion occurs, and no provider
publishing or customer pairing is part of this workflow. A queued workflow is not proof of a
successful deployment. GitHub schedule execution depends on the repository's Actions scheduler and the
owner-operated isolated runner. GitHub-hosted jobs are currently blocked by account
billing, so this controller does not use them. The controller uses the GitHub REST API
through its scoped Actions token, not an uninstalled `gh` executable. A separate
host-side heartbeat/runner watch is needed to detect missed schedules while the
runner itself is disconnected; a workflow cannot alert when it never starts.
