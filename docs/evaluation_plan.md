# Evaluation Plan

## Retrieval dataset

Begin with 40 questions, then expand to at least 100.

Include:

- Single-filing factual questions
- Section-specific questions
- Cross-period comparisons
- Cross-form questions
- Cross-company comparisons
- Unanswerable questions
- Ambiguous company or date questions

## Retrieval metrics

- Recall@5
- Recall@10
- Mean reciprocal rank
- nDCG@10
- Metadata-filter accuracy
- P50 and P95 latency
- Cost per query

## Answer metrics

- Claim support rate
- Citation precision
- Citation completeness
- Answer completeness
- Numeric accuracy
- Unsupported inference rate
- Correct abstention
- Critique correction rate

## Feedback refinement

Approved feedback becomes one of:

- New evaluation case
- Corrected relevant passage
- Hard negative
- Query-planning example
- Critique failure example
- Prompt regression case

A candidate configuration is promoted only when it does not regress critical metrics and improves the target failure category.
