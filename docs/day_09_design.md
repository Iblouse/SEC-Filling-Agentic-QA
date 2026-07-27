# Day 9 Design: Grounded SEC Question Answering

## Objective

Turn Day 8 reranked evidence into a direct answer while preserving deterministic provenance back to SEC chunks.

## Flow

1. Weighted RRF produces hybrid candidates.
2. Bedrock Cohere Rerank 3.5 reorders the candidate pool.
3. The top evidence chunks receive stable source labels `[S1]`, `[S2]`, and so on.
4. Amazon Nova 2 Lite receives only the user question plus the labeled SEC evidence.
5. The model must cite supplied source labels for factual claims or explicitly abstain.
6. Deterministic validation resolves citations back to full chunk IDs and rejects unknown citations.

## Model choice

Day 9 uses `us.amazon.nova-2-lite-v1:0` through the Amazon Bedrock Converse API. The model remains replaceable because the application uses the model-agnostic Converse interface.

## Evaluation

The frozen q001-q015 relevance judgments remain unchanged. Day 9 reports citation validity and whether generated answers cite chunks already judged relevant. These metrics measure provenance and evidence use, not full factual correctness. Manual review is still required for answer correctness.

## Deliberate boundary

Day 9 is a single-pass QA baseline. No critique, rewrite, or self-correction loop is added yet. That gives Day 10 a clean baseline against which to measure the value of critique and refinement.
