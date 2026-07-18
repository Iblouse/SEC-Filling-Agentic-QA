from __future__ import annotations

import json
import threading
import time
from collections.abc import Iterable
from datetime import date
from pathlib import Path
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from edgar_qa.sec.models import FilingManifest, FilingMetadata

SEC_DATA_BASE_URL = "https://data.sec.gov"
SEC_ARCHIVES_BASE_URL = "https://www.sec.gov/Archives/edgar/data"


class SecRequestError(RuntimeError):
    """Raised when an SEC request cannot be completed safely."""


class RateLimiter:
    """Thread-safe fixed-interval limiter for SEC requests."""

    def __init__(self, requests_per_second: float) -> None:
        self._interval = 1.0 / requests_per_second
        self._lock = threading.Lock()
        self._last_request_at = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            sleep_for = self._interval - (now - self._last_request_at)
            if sleep_for > 0:
                time.sleep(sleep_for)
            self._last_request_at = time.monotonic()


class SecClient:
    """SEC client with identification, throttling, retries, and normalization."""

    def __init__(
        self,
        user_agent: str,
        requests_per_second: float = 8.0,
        timeout_seconds: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not user_agent.strip() or "@" not in user_agent:
            raise ValueError("user_agent must identify the caller and include an email.")
        if not 0 < requests_per_second <= 10:
            raise ValueError("requests_per_second must be greater than 0 and no more than 10.")

        self._rate_limiter = RateLimiter(requests_per_second)
        self._client = httpx.Client(
            headers={
                "User-Agent": user_agent.strip(),
                "Accept-Encoding": "gzip, deflate",
                "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
            },
            timeout=timeout_seconds,
            follow_redirects=True,
            transport=transport,
        )

    def __enter__(self) -> SecClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    @retry(
        retry=retry_if_exception_type((httpx.TransportError, SecRequestError)),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
        reraise=True,
    )
    def _get_json(self, url: str) -> dict[str, Any]:
        self._rate_limiter.wait()
        response = self._client.get(url)

        if response.status_code == 429 or 500 <= response.status_code < 600:
            raise SecRequestError(f"Transient SEC response {response.status_code} for {url}.")

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise SecRequestError(
                f"SEC request failed with {response.status_code} for {url}."
            ) from exc

        payload = response.json()
        if not isinstance(payload, dict):
            raise SecRequestError(f"Expected a JSON object from {url}.")
        return payload

    @staticmethod
    def normalize_cik(cik: str | int) -> str:
        digits = "".join(character for character in str(cik) if character.isdigit())
        if not digits:
            raise ValueError("CIK must contain digits.")
        return digits.zfill(10)

    def get_company_submissions(self, cik: str | int) -> dict[str, Any]:
        normalized_cik = self.normalize_cik(cik)
        return self._get_json(f"{SEC_DATA_BASE_URL}/submissions/CIK{normalized_cik}.json")

    def build_manifest(
        self,
        cik: str | int,
        forms: Iterable[str] = ("10-K", "10-Q", "8-K"),
        since: date | None = None,
        limit: int | None = None,
    ) -> FilingManifest:
        payload = self.get_company_submissions(cik)
        return self.build_manifest_from_payload(
            cik=cik,
            payload=payload,
            forms=forms,
            since=since,
            limit=limit,
        )

    def build_manifest_from_payload(
        self,
        cik: str | int,
        payload: dict[str, Any],
        forms: Iterable[str] = ("10-K", "10-Q", "8-K"),
        since: date | None = None,
        limit: int | None = None,
    ) -> FilingManifest:
        normalized_cik = self.normalize_cik(cik)
        company_name = str(payload.get("name", "")).strip()
        recent = payload.get("filings", {}).get("recent", {})

        requested_forms = {form.strip().upper() for form in forms}
        filings: list[FilingMetadata] = []
        accessions = recent.get("accessionNumber", [])

        for index, accession_number in enumerate(accessions):
            form = str(recent["form"][index]).upper()
            if form not in requested_forms:
                continue

            filing_date = date.fromisoformat(recent["filingDate"][index])
            if since and filing_date < since:
                continue

            report_date_raw = recent.get("reportDate", [""] * len(accessions))[index]
            report_date = date.fromisoformat(report_date_raw) if report_date_raw else None
            primary_document = recent["primaryDocument"][index]
            compact_accession = accession_number.replace("-", "")
            cik_without_padding = str(int(normalized_cik))
            source_url = (
                f"{SEC_ARCHIVES_BASE_URL}/{cik_without_padding}/"
                f"{compact_accession}/{primary_document}"
            )

            filings.append(
                FilingMetadata(
                    cik=normalized_cik,
                    company_name=company_name,
                    accession_number=accession_number,
                    form=form,
                    filing_date=filing_date,
                    report_date=report_date,
                    primary_document=primary_document,
                    source_url=source_url,
                    is_inline_xbrl=bool(recent.get("isInlineXBRL", [0] * len(accessions))[index]),
                    file_number=_optional_index(recent.get("fileNumber"), index),
                    film_number=_optional_index(recent.get("filmNumber"), index),
                )
            )
            if limit is not None and len(filings) >= limit:
                break

        return FilingManifest(
            cik=normalized_cik,
            company_name=company_name,
            filings=filings,
        )

    @staticmethod
    def write_json(payload: dict[str, Any], output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
        temporary_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        temporary_path.replace(output_path)


def _optional_index(values: list[Any] | None, index: int) -> str | None:
    if not values or index >= len(values):
        return None
    value = str(values[index]).strip()
    return value or None
