"""Local-first parts search helpers."""
import hashlib
import json
import os
import re
from dataclasses import dataclass

from rapidfuzz import fuzz


STOPWORDS = {
    'a', 'an', 'and', 'are', 'for', 'in', 'is', 'it', 'of', 'on', 'or', 'part',
    'parts', 'the', 'to', 'with',
}


@dataclass
class SearchResult:
    part: object
    score: float
    why: str
    scorer_metadata: dict


class EmbeddingAdapter:
    """Provider-neutral interface for future semantic search providers."""

    def __init__(self, provider, model):
        self.provider = provider
        self.model = model

    def embed_text(self, text):
        raise NotImplementedError


def normalize_query(query):
    text = (query or '').lower()
    text = re.sub(r'[^a-z0-9]+', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def query_tokens(query):
    return {
        token for token in normalize_query(query).split()
        if token and token not in STOPWORDS
    }


def canonical_part_text(part):
    bins = []
    for bin in part.locations:
        bins.append(bin.name or '')
        bins.append(bin.full_label or '')
    return ' '.join([
        part.part_number or '',
        part.name or '',
        part.category or '',
        part.description or '',
        ' '.join(bins),
    ]).strip()


def canonical_part_hash(part):
    return hashlib.sha256(canonical_part_text(part).encode('utf-8')).hexdigest()


def _field_values(part):
    return [
        ('part number', part.part_number or ''),
        ('name', part.name or ''),
        ('category', part.category or ''),
        ('description', part.description or ''),
        ('bin', ' '.join(bin.name or '' for bin in part.locations)),
        ('bin label', ' '.join(bin.full_label or '' for bin in part.locations)),
    ]


def _best_field_score(query, part):
    best_label = 'part'
    best_score = 0
    for label, value in _field_values(part):
        if not value:
            continue
        score = fuzz.WRatio(query, value)
        if score > best_score:
            best_label = label
            best_score = score
    return best_label, best_score


def _feedback_boost(normalized_query, tokens, part, feedback_rows):
    boost = 0
    reasons = []
    for feedback in feedback_rows:
        if feedback.selected_part_id != part.id:
            continue
        if feedback.normalized_query == normalized_query:
            boost += 25
            reasons.append('previous correction')
            continue
        feedback_tokens = set(feedback.normalized_query.split()) - STOPWORDS
        if not tokens or not feedback_tokens:
            continue
        overlap = len(tokens & feedback_tokens) / len(tokens | feedback_tokens)
        if overlap >= 0.5:
            boost += 12
            reasons.append('similar correction')
    return min(boost, 35), reasons


def _intent_boost(tokens, part):
    boost = 0
    reasons = []
    if {'low', 'stock'} <= tokens or 'reorder' in tokens:
        if part.is_low_stock:
            boost += 12
            reasons.append('low stock')
    return boost, reasons


def get_embedding_provider():
    """Return configured embedding provider metadata, or None when disabled."""
    if os.environ.get('SEARCH_EMBEDDINGS_ENABLED', '0') != '1':
        return None
    provider = os.environ.get('SEARCH_EMBEDDINGS_PROVIDER', '').strip()
    api_key = os.environ.get('SEARCH_EMBEDDINGS_API_KEY', '').strip()
    model = os.environ.get('SEARCH_EMBEDDINGS_MODEL', '').strip()
    if not provider or not api_key or not model:
        return None
    return EmbeddingAdapter(provider, model)


def embedding_scores(query, parts, embeddings):
    """Provider-neutral placeholder for future semantic ranking."""
    adapter = get_embedding_provider()
    if not adapter:
        return {}
    return {}


def search_parts(query, parts, feedback_rows=None, embeddings=None, limit=25):
    normalized = normalize_query(query)
    tokens = query_tokens(query)
    feedback_rows = feedback_rows or []
    embeddings = embeddings or []
    semantic_scores = embedding_scores(query, parts, embeddings)
    results = []

    for part in parts:
        label, fuzzy_score = _best_field_score(normalized, part)
        searchable = normalize_query(canonical_part_text(part))
        token_hits = tokens & set(searchable.split())
        token_score = min(len(token_hits) * 8, 24)
        exact_part_number = normalized and normalized == normalize_query(part.part_number)
        exact_bonus = 45 if exact_part_number else 0
        feedback_boost, feedback_reasons = _feedback_boost(
            normalized, tokens, part, feedback_rows
        )
        intent_boost, intent_reasons = _intent_boost(tokens, part)
        semantic_score = semantic_scores.get(part.id, 0)
        score = fuzzy_score + token_score + exact_bonus + feedback_boost + intent_boost + semantic_score

        if score < 45 and not token_hits and not feedback_boost:
            continue

        reasons = []
        if exact_bonus:
            reasons.append('exact part number')
        elif label:
            reasons.append(f'{label} match')
        if token_hits:
            reasons.append('matched ' + ', '.join(sorted(token_hits)[:4]))
        reasons.extend(feedback_reasons)
        reasons.extend(intent_reasons)

        metadata = {
            'fuzzy_score': round(fuzzy_score, 2),
            'token_score': token_score,
            'exact_bonus': exact_bonus,
            'feedback_boost': feedback_boost,
            'intent_boost': intent_boost,
            'embedding_score': semantic_score,
            'matched_field': label,
            'matched_tokens': sorted(token_hits),
        }
        results.append(SearchResult(
            part=part,
            score=round(score, 2),
            why='; '.join(dict.fromkeys(reasons)) or 'close match',
            scorer_metadata=metadata,
        ))

    results.sort(key=lambda result: (-result.score, result.part.name.lower()))
    return results[:limit]


def encode_candidate_ids(results):
    return json.dumps([result.part.id for result in results])


def encode_scorer_metadata(results):
    return json.dumps({
        str(result.part.id): result.scorer_metadata
        for result in results
    })
