from __future__ import annotations

import os

os.environ.setdefault("ROLLBACK_TOKEN", "replace_me_with_a_local_token")
os.environ.setdefault("DATA_SOURCE", "sim")
os.environ["DEVOPSPILOT_FORCE_HEURISTIC"] = "1"
