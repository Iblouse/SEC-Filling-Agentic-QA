# Day 7 Design: Dense Semantic Retrieval Baseline

## Objective

Measure whether semantic embeddings improve evidence retrieval over the Day 6 BM25 baseline using exactly the same chunks, metadata filters, and manually labeled questions.

## Model

Use Amazon Titan Text Embeddings V2 through Amazon Bedrock Runtime.

Default configuration:

- Model ID: `amazon.titan-embed-text-v2:0`
- Dimensions: 512
- Normalize: true
- Similarity: cosine

The corpus representation includes company, form, filing date, section, and chunk text. This is an explicit retrieval experiment. Day 8 will test hybrid fusion and reranking rather than assuming dense retrieval is always superior.

## Why the vector index is local on Day 7

Day 7 is an evaluation step, not the final serving architecture. Keeping the vector matrix local makes the benchmark transparent and inexpensive to debug. A managed production search index will be added only after the retrieval configuration is selected.

## Reproducibility

The embedding cache records:

- Chunk ID
- Hash of the exact embedding input
- Model ID in the manifest
- Vector dimensions
- Normalization setting
- Corpus SHA-256
- Input token count

The cache is resumable. Existing chunk embeddings are not recomputed unless `--rebuild` is requested.

## Acceptance criteria

- Bedrock embedding invocation succeeds.
- Every corpus chunk has exactly one cached embedding.
- Semantic search respects SEC metadata filters.
- Dense retrieval is evaluated on the same labeled questions as BM25.
- Aggregate and per-query differences are documented.
- At least three cases are identified where BM25 and dense retrieval behave differently.
