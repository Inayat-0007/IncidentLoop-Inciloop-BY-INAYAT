---
name: threat-pass
description: Map a feature to the threat model, add abuse cases, and add negative tests. Use when adding features, auth, user input, or integrations.
---

# Threat pass

## Sequence

1. Read `docs/THREAT_MODEL.md` and `docs/CONTEXT.md`.
2. Map the change to assets, actors, entry points, and STRIDE rows.
3. List abuse cases (IDOR, missing auth, XSS, log injection, CORS, secret leak).
4. Add or update **negative tests** (at least unauthenticated and wrong-role when roles apply).
5. If a new never-do appears, add it to the threat model in the same PR — do not leave it in chat.

## Do not

- Treat “make it secure” in the prompt as a control.
- Skip tests because the happy path passes (SUSVIBES: functional ≠ secure).
