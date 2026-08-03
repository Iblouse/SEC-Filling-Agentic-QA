from __future__ import annotations

from edgar_qa.api.security import api_key_is_valid, path_requires_api_key


def test_only_versioned_api_paths_require_a_key() -> None:
    assert path_requires_api_key("/v1/answer")
    assert path_requires_api_key("/v1/feedback")
    assert not path_requires_api_key("/healthz")
    assert not path_requires_api_key("/readyz")


def test_api_key_validation_is_disabled_when_no_key_is_configured() -> None:
    assert api_key_is_valid(None, None)


def test_api_key_validation_requires_exact_match() -> None:
    assert api_key_is_valid("expected", "expected")
    assert not api_key_is_valid("wrong", "expected")
    assert not api_key_is_valid(None, "expected")
