# Day 8 completion checklist

- [ ] `make check` passes after applying the patch.
- [ ] The frozen dataset contains exactly q001 through q015.
- [ ] BM25 and dense reports both show 15 questions.
- [ ] Hybrid RRF search shows BM25 and dense component ranks.
- [ ] Hybrid RRF evaluation uses the same 15-question dataset.
- [ ] At least three questions are inspected manually across BM25, dense, and hybrid results.
- [ ] Bedrock direct rerank access is verified, or the exact IAM/model-access blocker is documented.
- [ ] Reranked hybrid evaluation is produced when model access is available.
- [ ] `day08_retrieval_comparison.json` compares all successfully evaluated systems.
- [ ] `docs/day_08_error_analysis.md` records at least three useful ranking observations.
- [ ] Day 8 code and documentation are committed and pushed.
