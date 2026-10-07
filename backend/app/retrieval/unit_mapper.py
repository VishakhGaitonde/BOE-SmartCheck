from collections import defaultdict

from app.embeddings.embedder import embed_text
from app.embeddings.vector_store import query_similar_filtered, tag_chunks_with_unit

TEXTBOOK_CANDIDATES_PER_UNIT = 15


def build_unit_textbook_map(paper_id: int, syllabus_chunks_by_unit: dict[str, str]) -> dict[str, list[dict]]:
    """
    For each syllabus unit, runs ONE broad textbook search using that
    unit's full syllabus content as the query, then permanently tags the
    matched textbook chunks with that unit label in the vector store —
    so later per-question retrieval can search within just that unit's
    textbook subset instead of the whole textbook collection every time.

    If a textbook chunk matches multiple units, it keeps the unit with
    the smallest (best) distance.
    """
    best_unit_for_chunk: dict[str, tuple[str, float]] = {}
    unit_results: dict[str, list[dict]] = defaultdict(list)

    for unit_label, unit_text in syllabus_chunks_by_unit.items():
        if not unit_text.strip():
            continue

        unit_embedding = embed_text(unit_text)
        matches = query_similar_filtered(
            paper_id, unit_embedding, top_k=TEXTBOOK_CANDIDATES_PER_UNIT, document_type="textbook"
        )

        for m in matches:
            chunk_id = m["id"]
            distance = m["distance"]
            unit_results[unit_label].append({
                "chunk_id": chunk_id,
                "distance": distance,
                "page": m["metadata"].get("page"),
            })

            current_best = best_unit_for_chunk.get(chunk_id)
            if current_best is None or distance < current_best[1]:
                best_unit_for_chunk[chunk_id] = (unit_label, distance)

    chunk_unit_map = {chunk_id: unit for chunk_id, (unit, _) in best_unit_for_chunk.items()}
    tag_chunks_with_unit(paper_id, chunk_unit_map)

    return unit_results