from __future__ import annotations


class GraphRunError(Exception):
    """Fail the investigation honestly (HTTP 4xx/5xx). Never a fake recommendation."""

    def __init__(self, status: int, code: str, detail: str) -> None:
        self.status = status
        self.code = code
        self.detail = detail
        super().__init__(detail)


class LlmError(GraphRunError):
    """Gemini (or configured vendor) failed. Not a heuristic fallback."""
