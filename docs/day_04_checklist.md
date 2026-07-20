# Day 4 Checklist

## Local validation

- [ ] Apply the patch.
- [ ] Make `scripts/run_day04_worker.sh` executable.
- [ ] Install the project again with development dependencies.
- [ ] Run `make check`.

## AWS execution

- [ ] Activate the `sec-qa` profile.
- [ ] Load Terraform outputs.
- [ ] Confirm Day 3 messages are available.
- [ ] Process one message.
- [ ] Verify the raw filing and receipt in S3.
- [ ] Verify S3 object metadata contains SHA-256, job ID, CIK, accession, and form.
- [ ] Rediscover the same filing and confirm `already_exists`.
- [ ] Drain the remaining test messages.

## Acceptance criterion

Day 4 is complete when at least five real SEC filing documents and their receipts exist in S3, duplicate processing does not overwrite them, and successfully processed messages are removed from SQS.
