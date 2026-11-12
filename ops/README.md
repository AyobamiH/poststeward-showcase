# Isolated Showcase runner maintenance

`cleanup-stale-runners.py` is the canonical, tested source of the existing
`poststeward-showcase-stale-runner-cleanup.service` on `web`. It is **not**
part of the website build or deployment. The systemd timer and JIT listener
remain host-managed; do not create a second timer or a deployment executor.

The tool defaults to a read-only dry run. Its `--apply` mode is limited to
5 runner removals per invocation (operator-selectable 0–10), only names with
the dedicated prefix, only offline + not busy, and at least one hour old.
It requires a complete registry and re-checks each candidate immediately
before removal. A failed or timed-out DELETE is **never retried**: the tool
reads back the full registry and reports absence only when independently
confirmed. API uncertainty, malformed results, pagination and unexpected
runner state fail closed. GET transport retries are bounded to 3 attempts;
authentication/permission failures are not retried.

Operator acceptance after an approved main merge: independently fetch the
exact merged source to the existing installed script path using atomic
replacement with rollback; verify SHA-256 source parity, keep existing unit
and timer configuration, and observe the next **natural** service execution.
No manual `--apply` call or unverified repeat after an uncertain effect.
A dry run is safe: `python3 -B ops/cleanup-stale-runners.py`.
Run hermetic regressions with
`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py' -v`.
