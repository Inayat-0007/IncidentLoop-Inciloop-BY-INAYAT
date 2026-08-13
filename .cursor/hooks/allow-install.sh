#!/usr/bin/env bash
# Pack-listed wrapper; Cursor hooks.json invokes the Node implementation (Windows-safe).
exec node "$(dirname "$0")/allow-install.mjs"
