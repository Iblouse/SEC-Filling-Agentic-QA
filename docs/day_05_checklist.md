# Day 5 Checklist: Parse Raw SEC Filings

## Local validation

- [ ] Apply the Day 5 patch.
- [ ] Run `python -m pip install -e ".[dev]"`.
- [ ] Run `make check`.
- [ ] Confirm the parser tests pass.

## AWS processing

- [ ] Activate the `sec-qa` AWS profile.
- [ ] Run `source scripts/load_day05_outputs.sh`.
- [ ] Parse one exact raw filing key.
- [ ] Inspect the curated JSON.
- [ ] Confirm title, blocks, tables, sections, and diagnostics exist.
- [ ] Parse at least five filings in a batch.
- [ ] Run the same batch again and confirm `already_exists` results.
- [ ] Review warnings and duplicate section labels.

## Acceptance criterion

Day 5 is complete when at least five raw filings have immutable curated JSON documents, stable identifiers, preserved tables, detected filing sections, and parsing diagnostics in the curated S3 bucket.
