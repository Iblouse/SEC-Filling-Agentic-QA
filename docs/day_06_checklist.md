# Day 6 Checklist: BM25 Retrieval Baseline

## Local validation

- [ ] Apply the patch.
- [ ] Make `scripts/run_day06_retrieval.sh` executable.
- [ ] Install the local package.
- [ ] Run `make check`.

## Corpus

- [ ] Load AWS bucket variables.
- [ ] Export all available curated documents to `data/retrieval/sec_chunks.jsonl`.
- [ ] Inspect `data/retrieval/corpus_manifest.json`.
- [ ] Confirm every record contains stable source metadata.
- [ ] Confirm no chunk crosses a section boundary.

## Search

- [ ] Run at least five business-oriented searches.
- [ ] Test a CIK or form filter.
- [ ] Inspect top results and note lexical failure cases.

## Evaluation

- [ ] Create an evaluation template.
- [ ] Edit the questions for clarity and business relevance.
- [ ] Label at least 10 questions with relevant chunk IDs.
- [ ] Run the BM25 evaluation.
- [ ] Save Recall@5, Recall@10, MRR, and nDCG@10.
- [ ] Record at least three retrieval failure categories.

## Acceptance criterion

Day 6 is complete when a reproducible BM25 baseline has been evaluated on at least 10 manually labeled questions and the report can be regenerated from a clean environment.
