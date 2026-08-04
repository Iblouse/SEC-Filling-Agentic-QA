from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


class FilingDownloadError(RuntimeError):
    """Raised when a filing cannot be safely downloaded."""


class FilingAccessBlockedError(FilingDownloadError):
    """Raised when SEC returns an automated-access block page."""


class FilingValidationError(FilingDownloadError):
    """Raised when a response is not a plausible filing document."""


class RateLimiter:
    def __init__(self, requests_per_second: float) -> None:
        if not 0 < requests_per_second <= 10:
            raise ValueError("requests_per_second must be greater than 0 and no more than 10.")
        self._interval = 1.0 / requests_per_second
        self._last_request = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            delay = self._interval - (now - self._last_request)
            if delay > 0:
                time.sleep(delay)
            self._last_request = time.monotonic()


@dataclass(frozen=True)
class DownloadedFiling:
    body: bytes
    content_sha256: str
    fetched_at: datetime
    content_type: str
    final_url: str
    etag: str | None
    last_modified: str | None


class SecFilingDownloader:
    _BLOCK_MARKERS = (
        b"undeclared automated tool",
        b"your request originates from an undeclared automated tool",
        b"request rate threshold exceeded",
    )

    def __init__(
        self,
        user_agent: str,
        requests_per_second: float = 8.0,
        timeout_seconds: float = 45.0,
        minimum_document_bytes: int = 200,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not user_agent.strip() or "@" not in user_agent:
            raise ValueError("user_agent must identify the caller and contain an email.")
        self._limiter = RateLimiter(requests_per_second)
        self._minimum_document_bytes = minimum_document_bytes
        self._client = httpx.Client(
            headers={
                "User-Agent": user_agent.strip(),
                "Accept-Encoding": "gzip, deflate",
                "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.5",
            },
            timeout=timeout_seconds,
            follow_redirects=True,
            transport=transport,
        )

    def __enter__(self) -> SecFilingDownloader:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    @retry(
        retry=retry_if_exception_type(
            (httpx.TransportError, httpx.TimeoutException, FilingAccessBlockedError)
        ),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=16),
        reraise=True,
    )
    def download(self, source_url: str) -> DownloadedFiling:
        self._limiter.wait()
        response = self._client.get(source_url)

        if response.status_code == 429 or 500 <= response.status_code < 600:
            raise FilingAccessBlockedError(
                f"Transient SEC response {response.status_code} for {source_url}."
            )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise FilingDownloadError(
                f"SEC request failed with {response.status_code} for {source_url}."
            ) from exc

        body = response.content
        prefix = body[:10000].lower()
        if any(marker in prefix for marker in self._BLOCK_MARKERS):
            raise FilingAccessBlockedError(
                "SEC returned an automated-access block page. Verify the user agent "
                "and reduce the request rate."
            )
        if len(body) < self._minimum_document_bytes:
            raise FilingValidationError(
                f"Downloaded document is unexpectedly small: {len(body)} bytes."
            )

        content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
        allowed = {
            "text/html",
            "application/xhtml+xml",
            "text/plain",
            "application/xml",
            "text/xml",
            "",
        }
        if content_type not in allowed:
            raise FilingValidationError(
                f"Unexpected filing content type: {content_type or '<missing>'}."
            )

        return DownloadedFiling(
            body=body,
            content_sha256=sha256(body).hexdigest(),
            fetched_at=datetime.now(UTC),
            content_type=content_type or "application/octet-stream",
            final_url=str(response.url),
            etag=response.headers.get("etag"),
            last_modified=response.headers.get("last-modified"),
        )
