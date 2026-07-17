import httpx

from edgar_qa.sec.client import SecClient

MOCK_SUBMISSIONS = {
    "cik": "19617",
    "name": "JPMORGAN CHASE & CO",
    "filings": {
        "recent": {
            "accessionNumber": [
                "0000019617-26-000001",
                "0000019617-26-000002",
                "0000019617-25-000003",
            ],
            "filingDate": ["2026-02-15", "2026-01-20", "2025-11-01"],
            "reportDate": ["2025-12-31", "2026-01-20", "2025-09-30"],
            "form": ["10-K", "8-K", "10-Q"],
            "fileNumber": ["001-05805", "001-05805", "001-05805"],
            "filmNumber": ["261234567", "261234568", "251234569"],
            "primaryDocument": ["jpm-20251231.htm", "jpm-8k.htm", "jpm-20250930.htm"],
            "isInlineXBRL": [1, 1, 1],
        }
    },
}


def test_build_manifest_filters_forms_and_constructs_source_url() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["user-agent"] == "Ibrahima Barry ibrahima@example.com"
        assert str(request.url).endswith("/submissions/CIK0000019617.json")
        return httpx.Response(200, json=MOCK_SUBMISSIONS)

    transport = httpx.MockTransport(handler)
    with SecClient(
        user_agent="Ibrahima Barry ibrahima@example.com",
        requests_per_second=10,
        transport=transport,
    ) as client:
        manifest = client.build_manifest("19617", forms=("10-K", "10-Q"))

    assert manifest.cik == "0000019617"
    assert [filing.form for filing in manifest.filings] == ["10-K", "10-Q"]
    assert (
        str(manifest.filings[0].source_url)
        == "https://www.sec.gov/Archives/edgar/data/19617/"
        "000001961726000001/jpm-20251231.htm"
    )


def test_rejects_non_identifiable_user_agent() -> None:
    try:
        SecClient(user_agent="anonymous")
    except ValueError as exc:
        assert "email" in str(exc)
    else:
        raise AssertionError("Expected an invalid user agent to be rejected.")
