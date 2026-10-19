from app.embeddings.embedder import embed_text, embed_texts, cosine_similarity
from app.embeddings.vector_store import query_similar, query_similar_filtered
from app.processing.syllabus_topics import split_into_subtopics
from app.reranking.reranker import rerank

DEFAULT_TOP_K = 5
RERANK_CANDIDATE_POOL = 15
SYLLABUS_MATCH_THRESHOLD = 0.55


def _best_matching_subtopic(question_text: str, question_embedding: list, syllabus_text: str) -> str:
    """
    Instead of using the ENTIRE top-matched syllabus chunk as textbook-search
    context (which blends every topic in that unit together and dilutes the
    signal — the same bug that broke unit-mapping before being fixed there),
    split that chunk into individual sub-topic phrases and pick only the ONE
    phrase most similar to the actual question. This keeps the textbook
    query narrowly focused on the specific sub-topic being asked about.
    """
    subtopics = split_into_subtopics(syllabus_text)
    if not subtopics:
        return syllabus_text[:400]

    subtopic_embeddings = embed_texts(subtopics)
    best_phrase, best_score = subtopics[0], -1.0
    for phrase, emb in zip(subtopics, subtopic_embeddings):
        score = cosine_similarity(question_embedding, emb)
        if score > best_score:
            best_score, best_phrase = score, phrase

    return best_phrase


def retrieve_evidence(paper_id: int, question_text: str, top_k: int = DEFAULT_TOP_K, unit_map_ready: bool = True) -> dict:
    question_embedding = embed_text(question_text)

    syllabus_candidates = query_similar(
        paper_id, question_embedding, top_k=RERANK_CANDIDATE_POOL, document_type="syllabus"
    )
    syllabus_matches = rerank(question_text, syllabus_candidates, top_k=top_k)

    matched_unit = syllabus_matches[0]["metadata"].get("chapter") if syllabus_matches else None
    syllabus_match_found = (
        len(syllabus_matches) > 0 and syllabus_matches[0]["distance"] <= SYLLABUS_MATCH_THRESHOLD
    )

    if syllabus_matches:
        focused_subtopic = _best_matching_subtopic(question_text, question_embedding, syllabus_matches[0]["text"])
        topic_query_text = f"{question_text}\n\nTopic context: {focused_subtopic}"
    else:
        topic_query_text = question_text

    topic_embedding = embed_text(topic_query_text)

    textbook_candidates = []
    used_narrowed_search = False

    if unit_map_ready and matched_unit:
        textbook_candidates = query_similar_filtered(
            paper_id, topic_embedding, top_k=RERANK_CANDIDATE_POOL, document_type="textbook", unit=matched_unit
        )
        used_narrowed_search = True

    if not textbook_candidates:
        textbook_candidates = query_similar_filtered(
            paper_id, topic_embedding, top_k=RERANK_CANDIDATE_POOL, document_type="textbook"
        )
        used_narrowed_search = False

    textbook_matches = rerank(topic_query_text, textbook_candidates, top_k=top_k)

    return {
        "syllabus_evidence": syllabus_matches,
        "textbook_evidence": textbook_matches,
        "syllabus_match_found": syllabus_match_found,
        "matched_unit": matched_unit,
        "used_narrowed_search": used_narrowed_search,
    }