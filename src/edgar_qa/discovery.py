from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, date, datetime

from pydantic import BaseModel

from edgar_qa.aws.queue import SqsFilingQueue
from edgar_qa.aws.storage import S3JsonStore, content_addressed_key
from edgar_qa.sec.client import SecClient
from edgar_qa.sec.models import FilingIngestionJob


class DiscoverySummary(BaseModel):
    cik: str
    company_name: str
    filing_count: int
    queued_count: int
    raw_submissions_key: str
    normalized_manifest_key: str
    raw_submissions_created: bool
    normalized_manifest_created: bool
    message_ids: list[str]


class FilingDiscoveryService:
    """Discovers filings once, persists immutable manifests, and queues downloads."""

    def __init__(
        self,
        sec_client: SecClient,
        raw_store: S3JsonStore,
        queue: SqsFilingQueue,
    ) -> None:
        self._sec_client = sec_client
        self._raw_store = raw_store
        self._queue = queue

    def discover(
        self,
        cik: str | int,
        forms: Iterable[str] = ("10-K", "10-Q", "8-K"),
        since: date | None = None,
        limit: int | None = None,
        discovered_at: datetime | None = None,
    ) -> DiscoverySummary:
        now = discovered_at or datetime.now(UTC)
        payload = self._sec_client.get_company_submissions(cik)
        manifest = self._sec_client.build_manifest_from_payload(
            cik=cik,
            payload=payload,
            forms=forms,
            since=since,
            limit=limit,
        )

        raw_key = content_addressed_key(f"manifests/sec-submissions/cik={manifest.cik}", payload)
        manifest_payload = manifest.model_dump(mode="json")
        normalized_key = content_addressed_key(
            f"manifests/normalized/cik={manifest.cik}", manifest_payload
        )

        raw_created = self._raw_store.put_if_absent(raw_key, payload)
        normalized_created = self._raw_store.put_if_absent(normalized_key, manifest_payload)

        message_ids: list[str] = []
        for filing in manifest.filings:
            job = FilingIngestionJob.from_filing(
                filing=filing,
                destination_bucket=self._raw_store.bucket,
                discovered_at=now,
            )
            message_ids.append(self._queue.send(job))

        return DiscoverySummary(
            cik=manifest.cik,
            company_name=manifest.company_name,
            filing_count=len(manifest.filings),
            queued_count=len(message_ids),
            raw_submissions_key=raw_key,
            normalized_manifest_key=normalized_key,
            raw_submissions_created=raw_created,
            normalized_manifest_created=normalized_created,
            message_ids=message_ids,
        )
