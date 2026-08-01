from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Protocol, cast

from pydantic import BaseModel, Field


class S3Body(Protocol):
    def read(self) -> bytes: ...


class S3Client(Protocol):
    def get_object(self, *, Bucket: str, Key: str) -> dict[str, object]: ...

    def download_file(self, bucket: str, key: str, filename: str) -> None: ...


class ArtifactFile(BaseModel):
    """One immutable runtime file referenced by the deployment manifest."""

    key: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    bytes: int = Field(ge=1)


class ArtifactManifest(BaseModel):
    """S3 manifest for the corpus and embedding cache loaded at API startup."""

    schema_version: int = Field(default=1, ge=1, le=1)
    corpus: ArtifactFile
    embeddings: ArtifactFile


class RuntimeArtifactPaths(BaseModel):
    corpus_path: Path
    embedding_cache_path: Path


def download_runtime_artifacts(
    client: S3Client,
    *,
    bucket: str,
    manifest_key: str,
    destination: Path,
) -> RuntimeArtifactPaths:
    """Download and verify the exact corpus and embedding files in an S3 manifest."""
    destination.mkdir(parents=True, exist_ok=True)
    manifest = _read_manifest(client, bucket, manifest_key)
    corpus_path = destination / "sec_chunks.jsonl"
    embedding_path = destination / "titan_v2_512_embeddings.jsonl"
    _download_verified(client, bucket, manifest.corpus, corpus_path)
    _download_verified(client, bucket, manifest.embeddings, embedding_path)
    return RuntimeArtifactPaths(
        corpus_path=corpus_path,
        embedding_cache_path=embedding_path,
    )


def _read_manifest(client: S3Client, bucket: str, key: str) -> ArtifactManifest:
    response = client.get_object(Bucket=bucket, Key=key)
    if "Body" not in response:
        raise ValueError("S3 artifact manifest response is missing Body.")
    body = cast(S3Body, response["Body"])
    raw = body.read()
    if not isinstance(raw, bytes):
        raise ValueError("S3 artifact manifest body did not return bytes.")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("S3 artifact manifest is not valid UTF-8 JSON.") from exc
    return ArtifactManifest.model_validate(payload)


def _download_verified(
    client: S3Client,
    bucket: str,
    artifact: ArtifactFile,
    target: Path,
) -> None:
    temporary = target.with_suffix(f"{target.suffix}.part")
    temporary.unlink(missing_ok=True)
    try:
        client.download_file(bucket, artifact.key, os.fspath(temporary))
        actual_size = temporary.stat().st_size
        if actual_size != artifact.bytes:
            raise ValueError(
                f"Artifact size mismatch for s3://{bucket}/{artifact.key}: "
                f"expected {artifact.bytes}, got {actual_size}."
            )
        actual_hash = _sha256(temporary)
        if actual_hash != artifact.sha256:
            raise ValueError(f"Artifact SHA-256 mismatch for s3://{bucket}/{artifact.key}.")
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
