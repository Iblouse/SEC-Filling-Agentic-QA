# Day 8 design: hybrid retrieval and reranking

Day 8 keeps the Day 7 relevance judgments frozen and introduces two increasingly expensive
retrieval stages.

1. BM25 and Titan dense retrieval independently produce candidate rankings.
2. Weighted Reciprocal Rank Fusion (RRF) combines ranks without comparing incompatible raw
   BM25 and cosine scores.
3. An optional Bedrock reranker reorders the fused candidate pool using the user question and
   the actual SEC text.

The default RRF configuration is equal weighting with `rrf_k=60`, `candidate_k=20`, and
`top_k=10`. The same metadata filters are passed to both first-stage retrievers.

Reranking is deliberately evaluated after RRF rather than replacing it. This produces four
comparable systems on the same frozen dataset: BM25, dense, RRF hybrid, and RRF plus reranker.

Do not relabel questions after seeing Day 8 rankings unless a relevance judgment is objectively
wrong. If a correction is necessary, document it and rerun every retrieval system.
