# PostSteward operation reference

Public showcase note: endpoint paths below are the real operation contract, but `poststeward.com` does not expose the effectful service. Use an authorised `<POSTSTEWARD_SERVICE_ORIGIN>`.

HTTP shape: `POST <POSTSTEWARD_SERVICE_ORIGIN>/api/operations/{name}` with `Authorization: Bearer <agent token>`.
Remote MCP exposes the same names as tools. Browser WebMCP registers the same scoped catalogue on a connected workspace.

## Free / always inspectable

| Operation | Scope | Effect | Purpose |
|---|---|---|---|
| `workspace_status` | read | READ_ONLY | Workspace, entitlement, limits and pause state |
| `accounts_list` | read | READ_ONLY | Verified identities and binding versions |
| `projects_list` | read | READ_ONLY | Explicit project routing |
| `campaign_get` | read | READ_ONLY | Exact stored text and digest |
| `campaign_validate` | read | READ_ONLY | Dry-run route/provider validation |
| `receipt_get` | read | READ_ONLY | One delivery and provider evidence |
| `receipts_list` | read | READ_ONLY | Delivery history |
| `workspace_export` | read | READ_ONLY | Export records without credentials/payment tokens |
| `automation_inspect` | read | READ_ONLY | Profiles, source snapshots and pending work |
| `billing_status` | read | READ_ONLY | Verified entitlement/payment method state |

## Mutations and consequences

Every mutation takes an `idempotencyKey`. Retry transport with the same key and exact inputs.

| Operation | Scope | Effect |
|---|---|---|
| `account_disconnect` | connections | AUTHORITY_CHANGE + FUTURE_CONSEQUENCE |
| `project_put` | campaign:write | STATE_WRITE |
| `campaign_create` | campaign:write | STATE_WRITE |
| `publish_now` | publish | STATE_WRITE + EXTERNAL_PROVIDER_EFFECT |
| `schedule_create` | schedule | STATE_WRITE + FUTURE_CONSEQUENCE |
| `schedule_cancel` | schedule | STATE_WRITE + FUTURE_CONSEQUENCE |
| `schedule_replace` | schedule | STATE_WRITE + FUTURE_CONSEQUENCE |
| `metrics_capture` | read | STATE_WRITE |
| `publishing_pause` | publish | AUTHORITY_CHANGE + FUTURE_CONSEQUENCE |

## Advanced continuing operation

| Operation | Scope | Tier | Effect |
|---|---|---|---|
| `automation_configure` | automation | Advanced | STATE_WRITE |
| `automation_preview` | automation | Advanced | READ_ONLY |
| `automation_enable` | automation | Advanced | AUTHORITY_CHANGE + FUTURE_CONSEQUENCE |
| `automation_pause` | automation | Always available to stop work | AUTHORITY_CHANGE + FUTURE_CONSEQUENCE |

Profiles start paused. Payment alone never starts posting.

## Billing

| Operation | Scope | Effect |
|---|---|---|
| `billing_quote` | billing | STATE_WRITE |
| `billing_checkout` | billing | FINANCIAL_EFFECT |
| `billing_portal` | billing | STATE_WRITE |

A checkout URL does not grant entitlement. Verified server payment state does.

## Receipt states

`scheduled`, `waiting_container`, `executing`, `published_verified`, `published_unverified`, `ambiguous_effect`, `drift_blocked`, `failed`, `cancelled`.

Never blindly retry `ambiguous_effect`.
