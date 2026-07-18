# Day 3 Checklist: EDGAR Discovery to AWS

## Goal

Discover recent SEC filings, persist immutable source and normalized manifests in S3, and publish one deterministic download job per filing to SQS.

## Setup

- [ ] Apply the Day 3 patch.
- [ ] Install the updated package with `python -m pip install -e ".[dev]"`.
- [ ] Run `pytest`.
- [ ] Activate the intended AWS profile.
- [ ] Load Terraform outputs into the current shell.

## First cloud run

- [ ] Discover five JPMorgan filings.
- [ ] Verify two manifest objects exist in the raw bucket.
- [ ] Verify five messages are visible or in flight on SQS.
- [ ] Inspect one message body without deleting it.
- [ ] Confirm every message contains a deterministic `job_id` and `destination_key`.

## Reliability checks

- [ ] Re-run the same discovery command.
- [ ] Confirm the manifest keys do not change for identical SEC responses.
- [ ] Confirm S3 does not overwrite existing manifest objects.
- [ ] Document that standard SQS provides at-least-once delivery.
- [ ] Confirm the future downloader will use `job_id` and `destination_key` for idempotency.

## Acceptance criterion

Day 3 is complete when a clean command discovers filings from SEC, stores immutable manifests in S3, queues deterministic jobs, and all local tests pass.
