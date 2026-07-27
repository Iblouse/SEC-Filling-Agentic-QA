# Day 7 Retrieval Comparison Notes

Fill this with actual results. Do not invent metrics.

## Aggregate metrics

| Metric | BM25 | Dense | Dense minus BM25 |
|---|---:|---:|---:|
| Recall@5 | | | |
| Recall@10 | | | |
| MRR | | | |
| nDCG@10 | | | |

## Cases where dense retrieval helped

1. Question:
   - BM25 behavior:
   - Dense behavior:
   - Likely reason:

2. Question:
   - BM25 behavior:
   - Dense behavior:
   - Likely reason:

## Cases where BM25 remained stronger

1. Question:
   - BM25 behavior:
   - Dense behavior:
   - Likely reason:

2. Question:
   - BM25 behavior:
   - Dense behavior:
   - Likely reason:

## Day 8 hypothesis

State what hybrid retrieval should improve, for example:

- Preserve exact financial/legal phrase matching from BM25.
- Recover synonym and paraphrase matches from dense retrieval.
- Reduce boilerplate or table-of-contents dominance.
- Rerank the fused candidate set using a stronger relevance model.
