# Product Requirements

## Product statement

A production-oriented research application for semantic search and question answering over SEC 10-K, 10-Q, and 8-K filings. It supports multi-filing questions, clause-level citations, a bounded critique loop, and user-feedback-driven offline refinement.

## Primary users

- Financial analysts
- Corporate legal and compliance analysts
- Investment research analysts
- Data scientists evaluating retrieval and generative AI systems

## First release use cases

1. Ask a question about one filing.
2. Compare the same disclosure across two periods.
3. Connect an 8-K event to later 10-Q or 10-K disclosure.
4. Compare disclosures among selected banks.
5. Inspect retrieved passages, citations, critique results, and revisions.

## Non-goals for v1

- Investment recommendations
- Legal advice
- Unrestricted autonomous agents
- Processing every EDGAR filer
- Real-time trading signals
- Fine-tuning a foundation model
- Automatic production changes from raw user feedback

## Initial acceptance targets

- Filing discovery success: at least 98%
- Retrieval Recall@5: at least 0.85
- Citation precision: at least 0.95
- Unsupported material claim rate: no more than 5%
- Correct abstention: at least 0.85
- Critical security failures: zero

Targets are acceptance criteria, not claimed results.
