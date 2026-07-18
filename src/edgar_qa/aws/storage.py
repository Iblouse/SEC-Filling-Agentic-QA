from __future__ import annotations

import hashlib
import json
from typing import Any

from botocore.exceptions import ClientError


def canonical_json_bytes(payload: Any) -> bytes:
    """Serialize a JSON-compatible value deterministically."""
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")


def content_addressed_key(prefix: str, payload: Any) -> str:
    body = canonical_json_bytes(payload)
    digest = hashlib.sha256(body).hexdigest()
    return f"{prefix.rstrip('/')}/sha256={digest}.json"


class S3JsonStore:
    """Writes immutable JSON records using conditional S3 puts."""

    def __init__(self, client: Any, bucket: str) -> None:
        self._client = client
        self.bucket = bucket

    def put_if_absent(self, key: str, payload: Any) -> bool:
        body = canonical_json_bytes(payload)
        try:
            self._client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=body,
                ContentType="application/json",
                IfNoneMatch="*",
            )
        except ClientError as exc:
            error = exc.response.get("Error", {})
            code = str(error.get("Code", ""))
            status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if code in {"PreconditionFailed", "ConditionalRequestConflict"} or status in {
                409,
                412,
            }:
                return False
            raise
        return True
