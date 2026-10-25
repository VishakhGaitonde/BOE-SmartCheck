from itertools import combinations
import numpy as np

from app.embeddings.embedder import embed_texts

LIKELY_DUPLICATE_THRESHOLD = 0.88
POSSIBLE_DUPLICATE_THRESHOLD = 0.72


def _cosine(a, b):
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))


def detect_duplicates(questions: list[dict]) -> list[dict]:
    """
    questions: [{"id": int, "text": str}]
    Only pairs crossing POSSIBLE_DUPLICATE_THRESHOLD are returned — pairs
    below it are UNIQUE by default and not persisted (matches spec: flag
    for BOE review, don't auto-reject; two questions on the same topic may
    still test different concepts).
    """
    if len(questions) < 2:
        return []

    embeddings = embed_texts([q["text"] for q in questions])

    results = []
    for i, j in combinations(range(len(questions)), 2):
        sim = _cosine(embeddings[i], embeddings[j])

        if sim >= LIKELY_DUPLICATE_THRESHOLD:
            status = "LIKELY_DUPLICATE"
        elif sim >= POSSIBLE_DUPLICATE_THRESHOLD:
            status = "POSSIBLE_DUPLICATE"
        else:
            continue

        results.append({
            "question_id_a": questions[i]["id"],
            "question_id_b": questions[j]["id"],
            "similarity": sim,
            "status": status,
            "explanation": (
                f"{'Nearly identical' if status == 'LIKELY_DUPLICATE' else 'Topically similar'} "
                f"(semantic similarity {sim:.2f}). Flagged for BOE review — may test the same "
                f"concept despite different wording, or may legitimately test different aspects."
            ),
        })

    return results