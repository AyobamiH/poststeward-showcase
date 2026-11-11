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

## Guarded lifecycle recovery (11 November 2026)

The dedicated listener's systemd `active` state is **not** evidence of an online
GitHub runner. GitHub can report the JIT registration offline while the
container is still alive; job acquire, TLS handshake and result upload can
fail independently of a successful TCP 443 probe. The release channel must
remain unchanged when that occurs.

`recover-offline-listener.py` is run by the five-minute timer. It requires a
complete authenticated GitHub runner registry, no online showcase runner, a
listener older than ten minutes, and two checks showing no active runner
worker. It rechecks GitHub before restarting only the dedicated showcase
service. An API error fails closed. Do not use it to terminate an active job.

`cleanup-stale-runners.py` runs hourly, deletes at most five registrations per
run, and only deletes exact-prefix, offline, non-busy JIT registrations older
than an hour. Each is individually re-read before deletion. The default is
read-only dry-run. It never removes online, busy, foreign or recent runners.

These are host-private owner-operated controls. Install their service/timer
files under `~/.config/systemd/user/` and Python scripts under
`~/.local/share/poststeward-showcase-runner/`, then `systemctl --user
daemon-reload` and enable the two timers. The GitHub Actions workflows and
Cloudflare production deployment gates remain authoritative. Do not mistake
recovery timers for an independently verified successful release.
