# Day 4 Design

1. Receive one SQS message with a visibility timeout.
2. Validate the versioned ingestion schema.
3. Check the deterministic S3 destination.
4. If present, treat the job as successful and delete the message.
5. Otherwise download from SEC with identification and rate limiting.
6. Reject block pages, implausibly small responses, and unexpected content types.
7. Calculate SHA-256 over the exact bytes.
8. Write the raw object with `If-None-Match: *`.
9. Write an immutable receipt with provenance and response metadata.
10. Delete the SQS message only after successful or idempotent completion.

A crash after S3 storage but before message deletion is safe. Redelivery finds the existing object and completes without overwriting it.
