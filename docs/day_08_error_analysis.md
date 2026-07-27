# Day 8 retrieval error analysis

Keep the q001-q015 relevance judgments frozen while completing this table.

| Question | BM25 behavior | Dense behavior | RRF behavior | Reranker behavior | Interpretation |
| --- | --- | --- | --- | --- | --- |
| q___ |  |  |  |  |  |
| q___ |  |  |  |  |  |
| q___ |  |  |  |  |  |

## Questions to answer

1. Which exact-term queries still favor BM25?
2. Which paraphrased questions favor dense retrieval?
3. Does RRF recover relevant chunks that only one first-stage retriever ranked highly?
4. Does reranking improve early precision or accidentally demote valid evidence?
5. Are any failures caused by chunk boundaries rather than ranking?
