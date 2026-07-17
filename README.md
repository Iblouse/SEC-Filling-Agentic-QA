# SEC Filing Agentic QA

Production-oriented semantic search and question answering over SEC 10-K, 10-Q, and 8-K filings, with a bounded critique loop and feedback-driven offline refinement.

## Initial scope

- Companies: JPMorgan Chase, Citigroup, Bank of America, Wells Fargo, Goldman Sachs
- Forms: 10-K, 10-Q, 8-K
- Cloud: AWS
- Local development: Python 3.11+

## Why this is not a PDF chatbot

1. Incremental EDGAR ingestion with immutable raw storage.
2. Stable filing and section metadata.
3. BM25, dense, and hybrid retrieval benchmarks.
4. Query planning for company, form, period, section, and comparison questions.
5. Claim-level citation verification.
6. A maximum of two critique-and-retrieval refinement cycles.
7. Structured user feedback and an approval-gated offline improvement pipeline.
8. Authentication, CI/CD, monitoring, cost tracking, and reproducible infrastructure.

## Start locally

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
pytest
```

Set a real SEC user agent in `.env`:

```text
SEC_USER_AGENT="Your Name your.email@example.com"
```

Retrieve a company's recent filing metadata:

```bash
edgar-qa submissions --cik 0000019617 --output data/raw/jpmorgan-submissions.json
```

List recent filings:

```bash
edgar-qa filings --cik 0000019617 --forms 10-K,10-Q,8-K --limit 20
```

## First acceptance gate

Before adding an LLM:

- Filing discovery is reproducible.
- Requests use an identifiable SEC user agent.
- Rate limiting and retry behavior are tested.
- Each filing has a stable accession number and source URL.
- Raw responses can be written without mutation.
- The manifest can be regenerated from a clean environment.
