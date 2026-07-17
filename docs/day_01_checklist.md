# Day 1 Checklist

## Product decisions

- [ ] Confirm the first five companies.
- [ ] Confirm forms: 10-K, 10-Q, and 8-K.
- [ ] Select the first three question modes.
- [ ] Write 20 realistic questions.
- [ ] Confirm v1 exclusions.
- [ ] Set initial evaluation targets.

## Local setup

- [ ] Copy `.env.example` to `.env`.
- [ ] Replace the SEC user agent with your name and contact email.
- [ ] Create and activate a Python 3.11 virtual environment.
- [ ] Install the package and development dependencies.
- [ ] Run `pytest`.
- [ ] Retrieve JPMorgan submissions metadata.
- [ ] List the most recent filings.
- [ ] Commit the initial repository.

## Acceptance criterion

Day 1 is complete when a clean environment can retrieve and normalize JPMorgan filing metadata through the CLI and all tests pass.
