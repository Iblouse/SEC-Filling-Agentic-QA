# Day 6 Design: Measurable BM25 Retrieval Baseline

## Purpose

Day 6 establishes a conventional lexical baseline before embeddings, reranking, or an LLM are introduced. Every later retrieval configuration must outperform or complement this baseline on the same labeled questions.

## Retrieval unit

The corpus uses section-aware chunks:

- Chunks never cross SEC item boundaries.
- A default chunk contains no more than 350 lexical terms.
- Adjacent chunks overlap by 50 terms.
- Large blocks are split into overlapping windows.
- Every chunk has a deterministic ID.
- Company, CIK, form, filing date, accession number, section label, section title, and source block IDs remain attached.

## Baseline

The implementation uses BM25 with:

- `k1 = 1.5`
- `b = 0.75`
- lowercase deterministic tokenization
- optional CIK, form, accession, and section filters

## Ground truth

Evaluation questions must be manually reviewed. Do not evaluate against LLM-generated relevance labels.

For each question:

1. Run BM25 search with the filing filters stored in the question.
2. Inspect the source chunks.
3. Record every chunk that contains sufficient supporting evidence.
4. Add relevant chunk IDs with the labeling command.
5. Add a note when relevance is ambiguous.

## Metrics

- Recall@5
- Recall@10
- Mean reciprocal rank
- nDCG@10

## Known limitations

- The baseline is lexical and may miss synonyms or paraphrases.
- Tokenized text does not preserve original punctuation or layout.
- The initial dataset is small and should not be presented as final system performance.
- Questions created by the template are starting points and should be edited for business relevance.
