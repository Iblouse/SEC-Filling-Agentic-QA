from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:['-][a-z0-9]+)?", re.IGNORECASE)


def tokenize(text: str) -> list[str]:
    """Return deterministic lowercase terms for the lexical baseline."""
    return [match.group(0).lower() for match in _TOKEN_RE.finditer(text)]
