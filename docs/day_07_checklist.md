# Day 7 Checklist

## Bedrock access

- [ ] Activate the `sec-qa` AWS profile.
- [ ] Confirm the account with STS.
- [ ] Run one Titan V2 verification embedding.

## Embedding cache

- [ ] Build a small five-chunk cache as a smoke test.
- [ ] Resume until every Day 6 chunk has an embedding.
- [ ] Verify the manifest says `complete: true`.
- [ ] Record total input tokens and embedding count.

## Semantic retrieval

- [ ] Search at least five Day 6 questions semantically.
- [ ] Verify CIK, form, accession, and section filters.
- [ ] Inspect examples where semantic ranking differs from BM25.

## Evaluation

- [ ] Evaluate dense retrieval against `evaluation/sec_questions.jsonl`.
- [ ] Compare BM25 and dense Recall@5, Recall@10, MRR, and nDCG@10.
- [ ] Document at least three retrieval differences.
- [ ] Do not change relevance labels after seeing the dense result unless the original label was objectively wrong; document any correction.

## Acceptance criterion

Day 7 is complete when the full corpus has embeddings, the dense evaluation report exists, the BM25 comparison exists, and the analysis identifies what hybrid retrieval should try to fix on Day 8.
