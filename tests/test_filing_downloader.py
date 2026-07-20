import httpx

from edgar_qa.ingestion.downloader import FilingAccessBlockedError, SecFilingDownloader


def test_downloader_hashes_valid_html() -> None:
    body = b"<html><body>" + b"financial filing text " * 20 + b"</body></html>"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=body,
            headers={"content-type": "text/html; charset=utf-8"},
            request=request,
        )

    with SecFilingDownloader(
        user_agent="Ibrahima Barry ibrahima@example.com",
        requests_per_second=10,
        transport=httpx.MockTransport(handler),
    ) as downloader:
        result = downloader.download("https://www.sec.gov/test.htm")

    assert result.body == body
    assert len(result.content_sha256) == 64
    assert result.content_type == "text/html"


def test_downloader_rejects_sec_block_page() -> None:
    body = (
        b"<html>Your Request Originates from an Undeclared Automated Tool"
        + b"x" * 300
        + b"</html>"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=body,
            headers={"content-type": "text/html"},
            request=request,
        )

    with SecFilingDownloader(
        user_agent="Ibrahima Barry ibrahima@example.com",
        requests_per_second=10,
        transport=httpx.MockTransport(handler),
    ) as downloader:
        try:
            downloader.download("https://www.sec.gov/test.htm")
        except FilingAccessBlockedError:
            pass
        else:
            raise AssertionError("Expected the SEC block page to be rejected.")
