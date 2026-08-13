#!/usr/bin/env python3
"""Ensure requirements.txt / frontend package.json names are on ALLOWED_DEPS.md and the registry."""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = (ROOT / "ALLOWED_DEPS.md").read_text(encoding="utf-8")


def allowed_names(section_header: str) -> set[str]:
    names: set[str] = set()
    in_section = False
    for line in ALLOWED.splitlines():
        if line.startswith("## "):
            in_section = line.strip() == section_header or line.startswith(section_header)
            if section_header in line:
                in_section = True
            elif line.startswith("## "):
                in_section = False
        if in_section and line.startswith("| ") and "Package" not in line and "---" not in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) > 1 and parts[1] and parts[1] != "Package":
                names.add(parts[1])
    return names


def req_names() -> list[str]:
    names = []
    for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        names.append(re.split(r"[<>=\[]", line, maxsplit=1)[0].strip())
    return names


def check_pypi(name: str) -> None:
    url = f"https://pypi.org/pypi/{name}/json"
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            if resp.status != 200:
                raise RuntimeError(name)
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"PyPI missing: {name} ({exc.code})") from exc


def main() -> int:
    pypi_allowed = allowed_names("## PyPI")
    if not pypi_allowed:
        pypi_allowed = allowed_names("PyPI")
    for name in req_names():
        if name not in pypi_allowed:
            print(f"not on ALLOWED_DEPS.md: {name}", file=sys.stderr)
            return 1
        check_pypi(name)

    pkg = ROOT / "frontend" / "package.json"
    if pkg.exists():
        npm_allowed = allowed_names("## npm")
        data = json.loads(pkg.read_text(encoding="utf-8"))
        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        for name in deps:
            if name not in npm_allowed:
                print(f"frontend dep not on ALLOWED_DEPS.md: {name}", file=sys.stderr)
                return 1
            url = f"https://registry.npmjs.org/{name}"
            try:
                with urllib.request.urlopen(url, timeout=20) as resp:
                    if resp.status != 200:
                        raise RuntimeError(name)
            except urllib.error.HTTPError as exc:
                raise SystemExit(f"npm missing: {name} ({exc.code})") from exc
    print("allowed deps ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
