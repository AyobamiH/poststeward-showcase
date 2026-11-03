# Showcase runner

Use the existing owner-authorised GitHub CLI session to register one ephemeral
runner per job for `AyobamiH/poststeward-showcase`. Do not copy that session,
Cloudflare secrets or user login credentials into the runner.

The listener uses the installed Node 24 runner image
`sha256:758e03ab2a553cf20f71c3495515d6966f125ca7bc1d94197597c4b25067e9f9`
and joins only `poststeward-showcase-net`. The egress sidecar reuses image
`sha256:f9e6f27cf17460dfb82250c5ac94f5a829956692c2e47615a870a4ec9312b802`,
with all capabilities dropped except `NET_ADMIN`, on its own Docker network
`poststeward-showcase-egress`. It has no host mounts. Its rules reject private,
link-local and metadata networks and disable IPv6 egress.

Install `listen.sh` under `~/.local/share/poststeward-showcase-runner/`, and the
service under `~/.config/systemd/user/`. Enable that service only after its
dedicated network sidecar reports `/tmp/network-ready`. Keep all product
PostSteward release, verification and observation services unchanged.

The same runner label accepts verification and deployment jobs, but each
job uses a new container and JIT registration. `CLOUDFLARE_API_TOKEN` remains
within the existing GitHub `showcase` environment and is delivered only to
the deployment job. Stop this service only when its active job has been
reconciled. Do not print the JIT configuration or process arguments.
