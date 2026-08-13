---
name: verify-deps
description: Verify package names exist on PyPI/npm and are on ALLOWED_DEPS.md before any install.
---

# Verify dependencies

## When

Adding or changing packages, or before `pip install` of a new name, `npm i` in `frontend/`.

## Steps

1. Read `ALLOWED_DEPS.md`. If the package is missing, **stop** and propose an allowlist update — do not install first.
2. Query the official registry (`https://pypi.org/pypi/<name>/json` or `npm view <name>`). If 404, **refuse**.
3. Confirm the name matches exactly.
4. Add the row to `ALLOWED_DEPS.md` in the same PR as `requirements.txt` / `frontend/package.json`.
5. Run `python scripts/verify_allowed_deps.py`.
6. Do not use unpinned `@latest` as the only constraint for app deps.

## Refuse

- Packages not on the registry
- Packages not on `ALLOWED_DEPS.md`
- `curl | sh` installers
