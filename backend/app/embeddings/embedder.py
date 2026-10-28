from sentence_transformers import SentenceTransformer

_model = None
MODEL_NAME = "all-MiniLM-L12-v2"  # ~3-5x faster than all-mpnet-base-v2 on CPU;
                                    # cross-encoder reranker compensates for the
                                    # slightly weaker initial embedding, so final
                                    # answer quality holds steady


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_model()
    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        show_progress_bar=False,
        normalize_embeddings=True,
        batch_size=64,  # up from default 32 — better CPU throughput, no accuracy change
    )
    return embeddings.tolist()


def embed_text(text: str) -> list[float]:
    return embed_texts([text])[0]


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    import numpy as np
    a, b = np.array(vec_a), np.array(vec_b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))