# Agent-readable catalogue parity — 2026-10-08

The live authenticated PostSteward operation authority is the **public**, read-only `https://app.poststeward.com/help.json` catalogue. The showcase remains a documentation-only surface and does not grant tokens, workspace access or publication authority.

This slice reconciles 50 operations from the accepted application release `abc23334b2c0ba01573945541513c466e72c999d` into `public/catalog.json`, the 50-item MCP metadata, machine help, OpenAPI operation name list and generated human operation reference. It includes standing authority (`autonomy_request`, `autonomy_list`, `autonomy_configure`, `autonomy_pause`) and corrects two earlier preparation operation schema/description drifts.

Manual agent deliveries retain their owner-review requirement. Separately, signed-in owner-configured standing authority may permit clean recurring production without per-copy approval; revocation, source/routing changes, editorial holds and uncertain effects remain fenced, and model spending requires its own consent.

`npm run verify` checks local cardinality, identity, scopes, consequences, human-reference and OpenAPI parity. `npm run verify:live-catalogue` compares every exposed operation field (excluding runtime availability) with the hosted public catalogue; the PR verification and daily GitHub drift workflow run this check. A mismatch is a **failed evidence check**, never permission to override the live app or to silently broaden authority.
