from __future__ import annotations

import secrets

PROTECTED_PATH_PREFIXES = ("/v1/",)


def path_requires_api_key(path: str) -> bool:
    """Return whether a request path belongs to the protected public API."""
    return any(path.startswith(prefix) for prefix in PROTECTED_PATH_PREFIXES)


def api_key_is_valid(provided: str | None, expected: str | None) -> bool:
    """Validate an API key without leaking timing information."""
    if expected is None:
        return True
    if provided is None:
        return False
    return secrets.compare_digest(provided, expected)
