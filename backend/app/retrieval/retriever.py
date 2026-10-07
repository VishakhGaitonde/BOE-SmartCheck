from app.embeddings.embedder import embed_text
from app.embeddings.vector_store import query_similar, query_similar_filtered

DEFAULT_TOP_K = 5
SYLLABUS_MATCH_THRESHOLD = 1.1


def retrieve_evidence(paper_id: int, question_text: str, top_k: int = DEFAULT_TOP_K, unit_map_ready: bool = True) -> dict:
    """
    1. Match question against syllabus -> determine its unit.
    2. If a unit->textbook map has been built (unit_map_ready=True), search
       textbook ONLY within that unit's pre-tagged chunks (fast, narrow).
       Otherwise fall back to searching the full textbook collection.
    """
    question_embedding = embed_text(question_text)

    syllabus_matches = query_similar(
        paper_id, question_embedding, top_k=top_k, document_type="syllabus"
    )

    syllabus_match_found = (
        len(syllabus_matches) > 0 and syllabus_matches[0]["distance"] <= SYLLABUS_MATCH_THRESHOLD
    )

    matched_unit = None
    if syllabus_match_found:
        matched_unit = syllabus_matches[0]["metadata"].get("chapter")

    top_syllabus_text = syllabus_matches[0]["text"] if syllabus_matches else ""
    topic_query_text = f"{question_text}\n\nTopic context: {top_syllabus_text[:400]}" if top_syllabus_text else question_text
    topic_embedding = embed_text(topic_query_text)

    textbook_matches = []
    used_narrowed_search = False

    if unit_map_ready and matched_unit:
        textbook_matches = query_similar_filtered(
            paper_id, topic_embedding, top_k=top_k, document_type="textbook", unit=matched_unit
        )
        used_narrowed_search = True

    if not textbook_matches:
        # Fall back to full-textbook search if narrowing found nothing
        # (e.g. unit map not built yet, or no chunks were tagged for this unit)
        textbook_matches = query_similar_filtered(
            paper_id, topic_embedding if syllabus_match_found else question_embedding,
            top_k=top_k, document_type="textbook"
        )
        used_narrowed_search = False

    return {
        "syllabus_evidence": syllabus_matches,
        "textbook_evidence": textbook_matches,
        "syllabus_match_found": syllabus_match_found,
        "matched_unit": matched_unit,
        "used_narrowed_search": used_narrowed_search,
    }