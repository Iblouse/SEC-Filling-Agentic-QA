# Evaluation Summary

## Active benchmark

The current committed benchmark contains 18 labeled questions:

- 13 JPMorgan Chase questions
- 5 Bank of America questions
- 5 Form 10-K questions
- 6 Form 10-Q questions
- 7 Form 8-K questions

Citigroup questions were removed from the active production benchmark after the parser could not produce canonical numbered sections for its 2025 Form 10-K.

## Retrieval results

The supplied local evaluation files contained per-query results for 24 questions. The release summary filters those records to the 18 question IDs currently committed in `evaluation/sec_questions.jsonl` and recomputes the aggregate means.

| System | Recall@5 | Recall@10 | MRR | nDCG@10 |
|---|---:|---:|---:|---:|
| BM25 | 0.456 | 0.515 | 0.583 | 0.521 |
| Titan dense cosine | 0.492 | 0.571 | **0.667** | 0.608 |
| Weighted reciprocal-rank fusion | **0.511** | **0.585** | 0.639 | **0.608** |
| Weighted RRF plus Cohere rerank | 0.489 | 0.567 | 0.611 | 0.570 |

### Interpretation

- Dense retrieval improved every reported metric over BM25.
- Weighted RRF produced the best recall and the highest nDCG by a small margin.
- Dense retrieval produced the best MRR, indicating the strongest average position of the first relevant result.
- Cohere reranking reduced aggregate performance on this benchmark. That finding is retained because production-oriented evaluation should expose regressions rather than assume that an additional model always improves quality.

## Grounded answer evaluation

The Day 9 evaluation covers q001 through q015:

| Metric | Result |
|---|---:|
| Questions | 15 |
| Answered | 10 |
| Abstention rate | 33.3% |
| Citation-validity rate | 93.3% |
| Gold-evidence hit rate | 60.0% |
| Mean cited-gold precision | 54.2% |
| Mean cited-gold recall | 25.6% |

The system used weighted RRF, Bedrock reranking, five evidence chunks, and Amazon Nova 2 Lite for answer generation.

## Bounded critique evaluation

The Day 10 evaluation uses the same q001 through q015 set:

| Metric | Result |
|---|---:|
| Revision rate | 20.0% |
| Final critic accept rate | 86.7% |
| Unresolved after revision | 20.0% |
| Final citation-validity rate | 86.7% |
| Final gold-evidence hit rate | 53.3% |
| Mean model calls | 2.4 |
| Mean model tokens | 3,811.2 |

The bounded workflow added explicit critique and a maximum of one revision, but it did not improve aggregate citation or evidence metrics. The correct engineering conclusion is that the workflow provides bounded review, traceability, and an explicit unresolved state. The current evidence does not support a claim that it improved answer quality.

## Release caveats

- The answer-generation and agentic evaluations cover 15 of the current 18 questions.
- A complete v1.0 evaluation rerun should evaluate all 18 active questions after the final production corpus is rebuilt and verified.
- Results are benchmark-specific and should not be generalized to all issuers or all SEC filing structures.
- The machine-readable summaries are stored under `evaluation/results/`.
