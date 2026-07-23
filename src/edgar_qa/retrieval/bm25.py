from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable

from edgar_qa.retrieval.models import RetrievalChunk, SearchFilters, SearchHit
from edgar_qa.retrieval.tokenization import tokenize


class BM25Index:
    """A small, transparent BM25 implementation for the lexical baseline."""

    def __init__(
        self,
        chunks: Iterable[RetrievalChunk],
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self.chunks = list(chunks)
        if not self.chunks:
            raise ValueError("BM25 requires at least one retrieval chunk.")
        if k1 <= 0:
            raise ValueError("k1 must be positive.")
        if not 0 <= b <= 1:
            raise ValueError("b must be between 0 and 1.")

        self.k1 = k1
        self.b = b
        self._term_frequencies = [Counter(tokenize(chunk.text)) for chunk in self.chunks]
        self._document_lengths = [sum(counter.values()) for counter in self._term_frequencies]
        self._average_document_length = sum(self._document_lengths) / len(self._document_lengths)
        self._document_frequency = self._build_document_frequency()

    def _build_document_frequency(self) -> Counter[str]:
        frequency: Counter[str] = Counter()
        for terms in self._term_frequencies:
            frequency.update(terms.keys())
        return frequency

    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: SearchFilters | None = None,
    ) -> list[SearchHit]:
        if top_k < 1:
            raise ValueError("top_k must be positive.")
        query_terms = tokenize(query)
        if not query_terms:
            return []

        scored: list[tuple[float, RetrievalChunk]] = []
        for index, chunk in enumerate(self.chunks):
            if not self._matches_filters(chunk, filters):
                continue
            score = self._score_document(index, query_terms)
            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda item: (-item[0], item[1].chunk_id))
        return [
            SearchHit(rank=rank, score=score, chunk=chunk)
            for rank, (score, chunk) in enumerate(scored[:top_k], start=1)
        ]

    def _score_document(self, index: int, query_terms: list[str]) -> float:
        frequencies = self._term_frequencies[index]
        document_length = self._document_lengths[index]
        score = 0.0
        number_of_documents = len(self.chunks)

        for term in set(query_terms):
            term_frequency = frequencies.get(term, 0)
            if term_frequency == 0:
                continue
            document_frequency = self._document_frequency[term]
            inverse_document_frequency = math.log(
                1 + (number_of_documents - document_frequency + 0.5) / (document_frequency + 0.5)
            )
            length_normalization = (
                1 - self.b + self.b * (document_length / self._average_document_length)
            )
            numerator = term_frequency * (self.k1 + 1)
            denominator = term_frequency + self.k1 * length_normalization
            score += inverse_document_frequency * numerator / denominator
        return score

    @staticmethod
    def _matches_filters(
        chunk: RetrievalChunk,
        filters: SearchFilters | None,
    ) -> bool:
        if filters is None:
            return True
        if filters.cik and chunk.cik != filters.cik.zfill(10):
            return False
        if filters.form and chunk.form.upper() != filters.form.upper():
            return False
        if filters.accession_number and chunk.accession_number != filters.accession_number:
            return False
        return not (
            filters.section_label and chunk.section_label.lower() != filters.section_label.lower()
        )
