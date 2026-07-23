# Day 6 BM25 Retrieval Error Analysis

## Benchmark summary

| Metric | Result |
|---|---:|
| Labeled questions | Pending |
| Recall@5 | 0.52
| Recall@10 | 0.52
| Mean reciprocal rank | 0.49
| nDCG@10 | Pending | 0.49401589388886324

## Failure categories

### 1. Vocabulary mismatch

- Question IDs:
- Expected evidence:
- Retrieved evidence:
- Why BM25 failed:
- Candidate improvement: dense retrieval or query expansion

### 2. Section or filing ambiguity

- Question IDs:
- Expected evidence:
- Retrieved evidence:
- Why BM25 failed:
- Candidate improvement: stronger metadata filters or query planning

### 3. Repeated boilerplate or table-of-contents headings

- Question IDs:
- Expected evidence:
- Retrieved evidence:
- Why BM25 failed:
- Candidate improvement: duplicate-section handling or section-occurrence weighting

## Decisions for the next experiment

- Chunking configuration to retain:
- Chunking configuration to change:
- Metadata filters to add:
- Questions requiring abstention:
- Hard negatives to preserve:
