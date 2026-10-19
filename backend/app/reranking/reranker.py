from sentence_transformers import CrossEncoder

_reranker = None
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def get_reranker():
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder(RERANKER_MODEL)
    return _reranker


def rerank(query: str, candidates: list[dict], top_k: int) -> list[dict]:
    """
    candidates: list of dicts each with a 'text' key (as returned by
    query_similar / query_similar_filtered).
    Re-scores all candidates against the query using a cross-encoder
    (which looks at query+passage together, far more precise than
    embedding cosine similarity alone), then returns the top_k by that
    score, each annotated with 'rerank_score'.
    """
    if not candidates:
        return []

    model = get_reranker()
    pairs = [[query, c["text"]] for c in candidates]
    scores = model.predict(pairs)

    for c, score in zip(candidates, scores):
        c["rerank_score"] = float(score)

    reranked = sorted(candidates, key=lambda c: c["rerank_score"], reverse=True)
    return reranked[:top_k]