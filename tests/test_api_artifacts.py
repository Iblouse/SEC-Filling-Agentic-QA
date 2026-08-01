from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import pytest

from edgar_qa.api.artifacts import download_runtime_artifacts


class FakeS3Client:
    def __init__(self, objects: dict[tuple[str, str], bytes]) -> None:
        self.objects = objects

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, object]:
        return {"Body": io.BytesIO(self.objects[(Bucket, Key)])}

    def download_file(self, bucket: str, key: str, filename: str) -> None:
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        Path(filename).write_bytes(self.objects[(bucket, key)])


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def test_download_runtime_artifacts_verifies_manifest(tmp_path: Path) -> None:
    bucket = "artifacts"
    corpus = b'{"chunk_id":"one"}\n'
    embeddings = b'{"chunk_id":"one","embedding":[0.1]}\n'
    corpus_key = "runtime/api/sec_chunks.jsonl"
    embeddings_key = "runtime/api/embeddings.jsonl"
    manifest = {
        "schema_version": 1,
        "corpus": {
            "key": corpus_key,
            "sha256": _sha256(corpus),
            "bytes": len(corpus),
        },
        "embeddings": {
            "key": embeddings_key,
            "sha256": _sha256(embeddings),
            "bytes": len(embeddings),
        },
    }
    client = FakeS3Client(
        {
            (bucket, "runtime/api/manifest.json"): json.dumps(manifest).encode(),
            (bucket, corpus_key): corpus,
            (bucket, embeddings_key): embeddings,
        }
    )

    paths = download_runtime_artifacts(
        client,
        bucket=bucket,
        manifest_key="runtime/api/manifest.json",
        destination=tmp_path,
    )

    assert paths.corpus_path.read_bytes() == corpus
    assert paths.embedding_cache_path.read_bytes() == embeddings


def test_download_runtime_artifacts_rejects_wrong_hash(tmp_path: Path) -> None:
    bucket = "artifacts"
    corpus = b"corpus"
    embeddings = b"embeddings"
    corpus_key = "runtime/api/sec_chunks.jsonl"
    embeddings_key = "runtime/api/embeddings.jsonl"
    manifest = {
        "schema_version": 1,
        "corpus": {
            "key": corpus_key,
            "sha256": "0" * 64,
            "bytes": len(corpus),
        },
        "embeddings": {
            "key": embeddings_key,
            "sha256": _sha256(embeddings),
            "bytes": len(embeddings),
        },
    }
    client = FakeS3Client(
        {
            (bucket, "runtime/api/manifest.json"): json.dumps(manifest).encode(),
            (bucket, corpus_key): corpus,
            (bucket, embeddings_key): embeddings,
        }
    )

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        download_runtime_artifacts(
            client,
            bucket=bucket,
            manifest_key="runtime/api/manifest.json",
            destination=tmp_path,
        )

    assert not (tmp_path / "sec_chunks.jsonl.part").exists()
