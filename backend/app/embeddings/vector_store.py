from pathlib import Path
import chromadb

CHROMA_DIR = Path(__file__).resolve().parent.parent.parent / "storage" / "chroma_db"
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

_client = None


def get_client():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return _client


def get_collection_name(paper_id: int) -> str:
    # One collection per paper keeps each verification session isolated.
    return f"paper_{paper_id}"


def get_or_create_collection(paper_id: int):
    client = get_client()
    return client.get_or_create_collection(name=get_collection_name(paper_id))


def delete_collection(paper_id: int):
    client = get_client()
    try:
        client.delete_collection(name=get_collection_name(paper_id))
    except Exception:
        pass  # collection may not exist yet


def add_chunks(paper_id: int, chunks: list[dict], embeddings: list[list[float]]):
    """
    chunks: list of dicts each with keys: id (str, unique), text, document_type,
            chapter, section, page
    embeddings: list of embedding vectors, same order/length as chunks
    """
    collection = get_or_create_collection(paper_id)

    ids = [c["id"] for c in chunks]
    documents = [c["text"] for c in chunks]
    metadatas = [
        {
            "document_type": c["document_type"],
            "chapter": c.get("chapter") or "",
            "section": c.get("section") or "",
            "page": c.get("page") if c.get("page") is not None else -1,
        }
        for c in chunks
    ]

    collection.add(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)


def query_similar(paper_id: int, query_embedding: list[float], top_k: int = 5, document_type: str | None = None):
    collection = get_or_create_collection(paper_id)

    where = {"document_type": document_type} if document_type else None

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where,
    )

    matches = []
    if results["ids"] and results["ids"][0]:
        for i in range(len(results["ids"][0])):
            matches.append({
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i],
            })
    return matches