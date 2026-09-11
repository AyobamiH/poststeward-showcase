# Security policy

## Repository scope

This repository is a static public showcase. It must never hold PostSteward owner sessions, provider access/refresh tokens, OAuth client secrets, Stripe secrets, signing keys or private customer data.

## Effect boundary

The showcase must not directly call social-provider APIs or reproduce canonical product write paths. Interactive controls are illustrative and explicitly labelled as simulation. Real account connections, approvals and publication stay inside `AyobamiH/poststeward`.

## Reporting

For a security concern in the showcase, open a private GitHub security advisory on this repository rather than posting secrets in a public issue.
