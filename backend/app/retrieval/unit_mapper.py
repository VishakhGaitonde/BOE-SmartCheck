import re
from collections import defaultdict

from app.embeddings.embedder import embed_text, embed_texts
from app.embeddings.vector_store import query_similar_filtered, tag_chunks_with_unit
from app.processing.syllabus_topics import split_into_subtopics

CANDIDATES_PER_SUBTOPIC = 12
MAX_CHUNKS_PER_UNIT = 60


def _split_into_subtopics(unit_text: str) -> list[str]:
    """
    Splits a unit's syllabus text into individual topic phrases (by sentence
    and colon-separated clause), instead of treating the whole unit as one
    blended query. A single combined embedding for a multi-topic unit (e.g.
    'Data Collection... Sampling Design... Testing of Hypotheses...') dilutes
    the signal toward whichever sub-topic dominates, causing genuinely
    distant sub-topics (like a separate hypothesis-testing chapter) to never
    surface in that unit's textbook candidates at all. Searching per
    sub-topic instead gives each one a fair, undiluted shot at retrieval.
    """
    # Remove boilerplate/noise lines first
    lines = [l for l in unit_text.split("\n") if l.strip() and not l.strip().startswith(("e ", "Unit"))]
    text = " ".join(lines)

    # Split on sentence end and on colons (syllabus topics are often
    # "Heading: subtopic1, subtopic2, subtopic3.")
    raw_parts = re.split(r'[.:]\s+', text)

    phrases = []
    for part in raw_parts:
        part = part.strip(" .,")
        if len(part) >= 15:  # skip tiny fragments
            phrases.append(part)

    return phrases if phrases else [unit_text]


def build_unit_textbook_map(paper_id: int, syllabus_chunks_by_unit: dict[str, str]) -> dict[str, list[dict]]:
    """
    For each syllabus unit, splits its content into individual sub-topic
    phrases and runs a SEPARATE textbook search for each one (rather than
    one blended search per unit), then merges and deduplicates the results.
    This ensures sub-topics with very different vocabulary from the rest of
    the unit (e.g. a distinct hypothesis-testing chapter within a broader
    "data collection" unit) still get properly represented in that unit's
    tagged textbook chunks.
    """
    best_unit_for_chunk: dict[str, tuple[str, float]] = {}
    unit_results: dict[str, list[dict]] = defaultdict(list)

    for unit_label, unit_text in syllabus_chunks_by_unit.items():
        if not unit_text.strip():
            continue

        subtopics = split_into_subtopics(unit_text)
        subtopic_embeddings = embed_texts(subtopics)

        seen_chunk_ids_this_unit = set()

        for subtopic_text, subtopic_embedding in zip(subtopics, subtopic_embeddings):
            matches = query_similar_filtered(
                paper_id, subtopic_embedding, top_k=CANDIDATES_PER_SUBTOPIC, document_type="textbook"
            )

            for m in matches:
                chunk_id = m["id"]
                distance = m["distance"]

                if chunk_id not in seen_chunk_ids_this_unit:
                    seen_chunk_ids_this_unit.add(chunk_id)
                    unit_results[unit_label].append({
                        "chunk_id": chunk_id,
                        "distance": distance,
                        "page": m["metadata"].get("page"),
                        "matched_subtopic": subtopic_text[:80],
                    })

                current_best = best_unit_for_chunk.get(chunk_id)
                if current_best is None or distance < current_best[1]:
                    best_unit_for_chunk[chunk_id] = (unit_label, distance)

        # Cap total chunks per unit to avoid runaway growth from many subtopics
        if len(unit_results[unit_label]) > MAX_CHUNKS_PER_UNIT:
            unit_results[unit_label].sort(key=lambda x: x["distance"])
            unit_results[unit_label] = unit_results[unit_label][:MAX_CHUNKS_PER_UNIT]

    chunk_unit_map = {chunk_id: unit for chunk_id, (unit, _) in best_unit_for_chunk.items()}
    tag_chunks_with_unit(paper_id, chunk_unit_map)

    return unit_results