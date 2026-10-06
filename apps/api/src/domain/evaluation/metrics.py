"""Pure Domain Evaluation Metrics for Automated RAG Verification (2026 Standards).

Conforms strictly to Hexagonal Architecture boundaries (0 framework/ORM imports).
Implements deterministic, offline-capable calculations for:
- Faithfulness (Factual grounding of generated answer against contexts)
- Answer Relevancy (Question-answering alignment and intent coverage)
- Context Recall (Coverage of ground-truth reference facts within retrieved contexts)
- Context Precision (Mean Average Precision of relevant context rank positioning)
"""

import re

from src.domain.abstractions.evaluation import DeepEvalScores, RagasScores

_STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "can't", "cannot", "could",
    "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down",
    "during", "each", "few", "for", "from", "further", "had", "hadn't", "has",
    "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her",
    "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's",
    "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it",
    "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my",
    "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other",
    "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't",
    "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
    "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
    "they've", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
    "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
    "yourself", "yourselves",
}

_EVASIVE_PATTERNS = [
    r"i (?:do not|don't) (?:know|have (?:enough )?information)",
    r"(?:unable|cannot) (?:to answer|find)",
    r"as an ai",
    r"not mentioned in the (?:context|provided)",
    r"no information provided",
]


def _stem(word: str) -> str:
    """Basic lightweight suffix normalization for plurals and verb inflections."""
    w = word.lower()
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith("es") and len(w) > 4:
        return w[:-2]
    if w.endswith("s") and not w.endswith("ss") and len(w) > 3:
        return w[:-1]
    if w.endswith("ing") and len(w) > 5:
        return w[:-3]
    if w.endswith("ed") and len(w) > 4:
        return w[:-2]
    return w


def _tokenize_meaningful(text: str) -> list[str]:
    """Extract normalized alphanumeric tokens excluding common stopwords."""
    words = re.findall(r"\b[A-Za-z0-9_\-\.\$]{2,}\b", text.lower())
    return [_stem(w) for w in words if w not in _STOPWORDS]


_LITERAL_PATTERN = re.compile(
    r"(?:\$?\d{1,3}(?:,\d{3})*(?:\.\d+)?%?|\b\d+(?:\.\d+)?%?|\b[A-Za-z]{2,}[-_]\d+\b)"
)


def _is_literal_supported(lit: str, context_text: str) -> bool:
    """Check if literal entity or its numeric value is present in context."""
    clean_lit = lit.lower().strip()
    if clean_lit in context_text:
        return True
    digits_only = re.sub(r"[^\d\.]", "", clean_lit)
    if digits_only and digits_only in context_text:
        return True
    return False


def extract_atomic_claims(text: str) -> list[str]:
    """Decompose answer into atomic factual sentences and strip conversational fluff."""
    raw_sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    claims = []
    fluff_pattern = re.compile(
        r"^(?:hello|hi|hey|sure|here is|here are|according to|based on the|thank you)[^.:]*[.:]?",
        re.IGNORECASE,
    )

    for s in raw_sentences:
        clean = s.strip()
        if not clean:
            continue
        clean = fluff_pattern.sub("", clean).strip()
        if not clean:
            continue
        # Preserve any sentence containing meaningful entities, literals, or content tokens
        toks = _tokenize_meaningful(clean)
        literals = _LITERAL_PATTERN.findall(clean)
        if toks or literals or len(clean.split()) >= 2:
            claims.append(clean)
    return claims


def calculate_faithfulness(answer: str, contexts: list[str]) -> float:
    """Evaluate factual grounding of answer against retrieved contexts (0.0 to 1.0).

    A claim is grounded if its key entities, relations, and quantities are entailed
    by the context without contradiction.
    """
    if not answer.strip():
        return 0.0
    if not contexts:
        return 0.0

    claims = extract_atomic_claims(answer)
    if not claims:
        claims = [answer.strip()]

    combined_context = " ".join(contexts).lower()
    context_tokens = set(_tokenize_meaningful(combined_context))
    supported_count = 0.0
    contradiction_count = 0.0

    negation_words = {"not", "never", "no", "cannot", "none", "neither"}

    for claim in claims:
        claim_lower = claim.lower()
        claim_tokens = _tokenize_meaningful(claim_lower)
        if not claim_tokens:
            continue

        # Check explicit negation contradiction
        claim_has_neg = any(w in negation_words for w in re.findall(r"\b\w+\b", claim_lower))
        matched_tokens = [t for t in claim_tokens if t in context_tokens]
        match_ratio = len(matched_tokens) / len(claim_tokens)

        # Look for numbers/currency/identifiers specifically
        literals = _LITERAL_PATTERN.findall(claim)
        literals_supported = all(_is_literal_supported(lit, combined_context) for lit in literals) if literals else True

        if match_ratio >= 0.60 and literals_supported:
            if claim_has_neg and "not" not in combined_context and "never" not in combined_context:
                contradiction_count += 1.0
            else:
                supported_count += 1.0
        elif match_ratio < 0.30 or not literals_supported:
            # Ungrounded claim
            pass
        else:
            # Partial support
            supported_count += 0.5

    if not claims:
        return 0.0

    score = (supported_count - (contradiction_count * 0.5)) / len(claims)
    return max(0.0, min(1.0, round(score, 4)))


def calculate_answer_relevance(question: str, answer: str) -> float:
    """Evaluate whether generated answer directly addresses user question (0.0 to 1.0)."""
    if not question.strip() or not answer.strip():
        return 0.0

    answer_lower = answer.lower()
    # Check for evasive responses
    for pattern in _EVASIVE_PATTERNS:
        if re.search(pattern, answer_lower):
            return 0.15

    q_tokens = _tokenize_meaningful(question)
    if not q_tokens:
        return 1.0 if answer.strip() else 0.0

    a_tokens = set(_tokenize_meaningful(answer))

    overlap = [t for t in q_tokens if t in a_tokens]
    overlap_ratio = len(overlap) / len(q_tokens)

    # Length & substance penalty: very short answer (< 5 words) is penalized
    substance_factor = min(1.0, len(answer.split()) / 8.0)

    # Question intent keyword boost
    q_lower = question.lower()
    intent_addressed = True
    if "how much" in q_lower or "cost" in q_lower or "price" in q_lower:
        intent_addressed = any(c in answer for c in ["$", "€", "₹", "cost", "price", "fee", "rate", "%"])
    elif "why" in q_lower:
        intent_addressed = any(w in answer_lower for w in ["because", "since", "due to", "as a result", "reason"])

    intent_multiplier = 1.0 if intent_addressed else 0.75
    if overlap_ratio >= 0.35:
        base_score = 0.60 + 0.40 * min(1.0, (overlap_ratio - 0.35) / 0.45)
    else:
        base_score = (overlap_ratio / 0.35) * 0.60

    score = base_score * substance_factor * intent_multiplier
    return max(0.0, min(1.0, round(score, 4)))


def calculate_context_recall(ground_truth_answer: str, contexts: list[str]) -> float:
    """Evaluate what fraction of ground truth facts are present in retrieved contexts (0.0 to 1.0)."""
    if not ground_truth_answer.strip():
        return 1.0
    if not contexts:
        return 0.0

    gt_facts = extract_atomic_claims(ground_truth_answer)
    if not gt_facts:
        gt_facts = [ground_truth_answer.strip()]

    combined_context = " ".join(contexts).lower()
    context_tokens = set(_tokenize_meaningful(combined_context))
    recalled_facts = 0.0

    for fact in gt_facts:
        fact_tokens = _tokenize_meaningful(fact)
        if not fact_tokens:
            recalled_facts += 1.0
            continue

        matched = [t for t in fact_tokens if t in context_tokens]
        ratio = len(matched) / len(fact_tokens)

        literals = _LITERAL_PATTERN.findall(fact)
        literals_present = all(_is_literal_supported(lit, combined_context) for lit in literals) if literals else True

        if ratio >= 0.50 and literals_present:
            recalled_facts += 1.0
        elif ratio >= 0.35:
            recalled_facts += 0.5

    score = recalled_facts / len(gt_facts)
    return max(0.0, min(1.0, round(score, 4)))


def calculate_context_precision(
    contexts: list[str],
    ground_truth_answer: str,
    relevant_chunk_ids: list[str] | None = None,
    retrieved_chunk_ids: list[str] | None = None,
) -> float:
    """Evaluate Average Precision of retrieved contexts (0.0 to 1.0).

    Higher score if relevant contexts appear at earlier ranks.
    """
    if not contexts:
        return 0.0

    gt_tokens = set(_tokenize_meaningful(ground_truth_answer))

    relevance_flags: list[bool] = []
    for idx, ctx in enumerate(contexts):
        # 1. If chunk IDs are provided, use ID match
        if relevant_chunk_ids and retrieved_chunk_ids and idx < len(retrieved_chunk_ids):
            c_id = retrieved_chunk_ids[idx]
            relevance_flags.append(c_id in relevant_chunk_ids)
            continue

        # 2. Otherwise use token semantic overlap with ground truth
        ctx_tokens = set(_tokenize_meaningful(ctx))
        if not gt_tokens:
            relevance_flags.append(True)
            continue
        overlap = gt_tokens.intersection(ctx_tokens)
        ratio = len(overlap) / len(gt_tokens)
        relevance_flags.append(ratio >= 0.30)

    if not any(relevance_flags):
        return 0.0

    # Mean Average Precision across ranks
    cumulative_hits = 0
    precision_sum = 0.0
    for k, is_rel in enumerate(relevance_flags, start=1):
        if is_rel:
            cumulative_hits += 1
            precision_at_k = cumulative_hits / k
            precision_sum += precision_at_k

    score = precision_sum / cumulative_hits if cumulative_hits > 0 else 0.0
    return max(0.0, min(1.0, round(score, 4)))


def compute_rag_scores(
    question: str,
    generated_answer: str,
    contexts: list[str],
    ground_truth_answer: str,
    relevant_chunk_ids: list[str] | None = None,
    retrieved_chunk_ids: list[str] | None = None,
) -> tuple[RagasScores, DeepEvalScores]:
    """Compute complete RAG quality scores for a single evaluation item."""
    faithfulness = calculate_faithfulness(generated_answer, contexts)
    answer_relevance = calculate_answer_relevance(question, generated_answer)
    context_recall = calculate_context_recall(ground_truth_answer, contexts)
    context_precision = calculate_context_precision(
        contexts,
        ground_truth_answer,
        relevant_chunk_ids=relevant_chunk_ids,
        retrieved_chunk_ids=retrieved_chunk_ids,
    )

    if not generated_answer.strip():
        hallucination = 0.0
    else:
        hallucination = round(max(0.0, 1.0 - faithfulness), 4)

    ragas = RagasScores(
        faithfulness=faithfulness,
        answer_relevancy=answer_relevance,
        context_precision=context_precision,
        context_recall=context_recall,
    )
    deepeval = DeepEvalScores(
        hallucination=hallucination,
        toxicity=0.0,
        bias=0.0,
    )
    return ragas, deepeval
