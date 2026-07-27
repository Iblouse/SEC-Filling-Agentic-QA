from __future__ import annotations

import re
from collections.abc import Sequence

from edgar_qa.qa.models import EvidenceSource

_CITATION_PATTERN = re.compile(r"\[S(\d+)\]")
_ABSTAIN_PREFIX = "INSUFFICIENT_EVIDENCE"


def extract_citations(answer: str) -> list[str]:
    """Return unique citations in first-appearance order."""
    citations: list[str] = []
    for match in _CITATION_PATTERN.finditer(answer):
        citation = f"S{match.group(1)}"
        if citation not in citations:
            citations.append(citation)
    return citations


def is_abstention(answer: str) -> bool:
    return answer.strip().upper().startswith(_ABSTAIN_PREFIX)


def validate_answer_citations(
    answer: str,
    sources: Sequence[EvidenceSource],
) -> tuple[list[str], list[str], bool, bool, list[str]]:
    """Validate that answer citations resolve only to supplied evidence sources."""
    citations = extract_citations(answer)
    source_map = {source.source_id: source for source in sources}
    abstained = is_abstention(answer)
    errors: list[str] = []

    unknown = [citation for citation in citations if citation not in source_map]
    if unknown:
        errors.append(f"Unknown citation(s): {', '.join(unknown)}")
    if abstained and citations:
        errors.append("Abstentions must not cite evidence sources.")
    if not abstained and not citations:
        errors.append("A non-abstaining answer must cite at least one evidence source.")

    cited_chunk_ids = [
        source_map[citation].chunk_id for citation in citations if citation in source_map
    ]
    return citations, cited_chunk_ids, abstained, not errors, errors
