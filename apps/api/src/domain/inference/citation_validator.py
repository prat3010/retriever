"""Citation Validator Service.

Inspects token stream content for inline source citations like
[Source: chunk_id] and verifies they match the set of retrieved
chunk IDs. Depends only on domain abstractions.
"""

import re

CITATION_PATTERN = re.compile(r"\[Source:\s*([^\]]+)\]")


class CitationValidator:
    """Validates that inline citations in generated text reference real chunks."""

    def __init__(self) -> None:
        self._valid_ids: set[str] = set()

    def set_valid_ids(self, chunk_ids: list[str]) -> None:
        """Register the set of allowable chunk IDs for this generation."""
        self._valid_ids = set(chunk_ids)

    def extract_citations(self, text: str) -> list[str]:
        """Extract all cited chunk IDs from generated text."""
        return CITATION_PATTERN.findall(text)

    def validate(self, text: str) -> bool:
        """Check all citations in text reference known chunk IDs.

        Returns True if all citations are valid (or there are none).
        """
        cited = self.extract_citations(text)
        if not cited:
            return True
        return all(cid in self._valid_ids for cid in cited)

    def get_invalid_citations(self, text: str) -> list[str]:
        """Return list of cited chunk IDs that are NOT in the valid set."""
        cited = self.extract_citations(text)
        return [cid for cid in cited if cid not in self._valid_ids]

    def strip_invalid_citations(self, text: str) -> str:
        """Remove all [Source: X] tokens where X is NOT in valid_ids."""
        def _replacer(match):
            cid = match.group(1)
            return "" if cid not in self._valid_ids else match.group(0)
        return CITATION_PATTERN.sub(_replacer, text)

    def validate_sentence_attribution(
        self, text: str, chunk_contents: dict[str, str]
    ) -> dict[str, bool]:
        """Audit cited chunk IDs against provided chunk content to verify semantic grounding.

        Returns a dict mapping chunk_id to boolean indicating whether cited chunk content overlaps
        lexically or semantically with the claim text.
        """
        cited_ids = set(self.extract_citations(text))
        attribution_results: dict[str, bool] = {}

        # Tokenize sentence keywords (ignoring short stopwords)
        words = set(re.findall(r"\b[a-zA-Z0-9]{4,}\b", text.lower()))

        for cid in cited_ids:
            if cid not in self._valid_ids or cid not in chunk_contents:
                attribution_results[cid] = False
                continue

            chunk_text = chunk_contents[cid].lower()
            overlap = any(w in chunk_text for w in words)
            attribution_results[cid] = overlap

        return attribution_results

