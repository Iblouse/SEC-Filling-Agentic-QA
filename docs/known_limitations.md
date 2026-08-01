# Known Limitations

## Citigroup filing-section parsing

The production-supported issuer set currently consists of:

- JPMorgan Chase
- Bank of America

Citigroup remains experimental.

The Citigroup 2025 Form 10-K was downloaded and converted into 4,159
content blocks, but the filing did not expose SEC item numbers such as
"Item 1A" in the extracted visible block text. It exposed title-only
headings such as "RISK FACTORS."

The current parser recognizes numbered SEC item headings. Because no
numbered headings were detected, it correctly activated its fallback
behavior and produced one `document` section covering the complete filing.

This resulted in document-level retrieval chunks rather than canonical
sections such as `item-1a`. Citigroup was therefore removed from the
production corpus rather than serving unverified section-level results.

Future parser hardening should add:

- Form-specific title-to-item mappings
- Duplicate and table-of-contents rejection
- Expected SEC section-order validation
- Citigroup parser regression fixtures
- Structural corpus tests before embedding generation
