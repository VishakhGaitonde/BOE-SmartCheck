from app.embeddings.embedder import embed_text
from app.embeddings.vector_store import query_similar

DEFAULT_TOP_K = 5

# Below this distance, we consider the syllabus match strong enough to trust.
# ChromaDB default distance is cosine distance — lower is more similar.
SYLLABUS_MATCH_THRESHOLD = 1.1


def retrieve_evidence(paper_id: int, question_text: str, top_k: int = DEFAULT_TOP_K) -> dict:
    """
    Two-stage retrieval:
    1. Match the question against the SYLLABUS first — this tells us which
       topic/unit the question is supposed to belong to.
    2. Use that matched syllabus topic (not just the raw question) to search
       the TEXTBOOK — since the syllabus is the subset/index of what the
       textbook should cover, we confirm the textbook actually supports
       that specific topic, not just generic wording overlap with the question.
    """
    question_embedding = embed_text(question_text)

    syllabus_matches = query_similar(
        paper_id, question_embedding, top_k=top_k, document_type="syllabus"
    )

    syllabus_match_found = (
        len(syllabus_matches) > 0 and syllabus_matches[0]["distance"] <= SYLLABUS_MATCH_THRESHOLD
    )

    if syllabus_match_found:
        # Build a topic-anchored query: question + the best-matching syllabus
        # content, so textbook retrieval is guided by the actual curriculum
        # topic rather than just the question's own wording.
        top_syllabus_text = syllabus_matches[0]["text"]
        topic_query_text = f"{question_text}\n\nTopic context: {top_syllabus_text[:400]}"
        topic_embedding = embed_text(topic_query_text)
        textbook_matches = query_similar(
            paper_id, topic_embedding, top_k=top_k, document_type="textbook"
        )
    else:
        # No confident syllabus match — still search textbook on the raw
        # question so the BOE can see whether ANY supporting content exists,
        # but this case should be flagged more cautiously downstream (Phase 10).
        textbook_matches = query_similar(
            paper_id, question_embedding, top_k=top_k, document_type="textbook"
        )

    return {
        "syllabus_evidence": syllabus_matches,
        "textbook_evidence": textbook_matches,
        "syllabus_match_found": syllabus_match_found,
    }


def retrieve_for_all_questions(paper_id: int, questions: list[dict], top_k: int = DEFAULT_TOP_K) -> list[dict]:
    results = []
    for q in questions:
        evidence = retrieve_evidence(paper_id, q["question_text"], top_k=top_k)
        results.append({
            "question_id": q["id"],
            "syllabus_evidence": evidence["syllabus_evidence"],
            "textbook_evidence": evidence["textbook_evidence"],
            "syllabus_match_found": evidence["syllabus_match_found"],
        })
    return results