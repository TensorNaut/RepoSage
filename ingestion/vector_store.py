import chromadb
from sentence_transformers import SentenceTransformer
import json, os

# Embedding model
MODEL = SentenceTransformer("all-MiniLM-L6-v2")

# ChromaDB client — stores data in a local folder called "chroma_db"
CLIENT = chromadb.PersistentClient(path="./chroma_db")


def _get_or_create_collection(name: str):
    """Get existing collection or create it fresh."""
    return CLIENT.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"}  # use cosine similarity for text
    )



def store_chunks(chunks: list[dict], collection_name: str, batch_size: int = 100):
    """
    Embed all chunks and store them in ChromaDB.
    
    Each chunk needs:
      - id        : unique string ID
      - embedding : vector from the model
      - document  : the raw text (ChromaDB stores this too)
      - metadata  : our structured fields
    """
    if not chunks:
        print(f"No chunks to store in '{collection_name}'")
        return

    clear_collection(collection_name)

    collection = _get_or_create_collection(collection_name)

    # Process in batches to avoid memory issues with large repos
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]

        texts     = [c["text"] for c in batch]
        metadatas = [c["metadata"] for c in batch]
        ids       = [f"{collection_name}_{i + j}" for j, _ in enumerate(batch)]

        # Generate embeddings — this is the heavy step
        embeddings = MODEL.encode(texts, show_progress_bar=False).tolist()

        collection.add(
            ids        = ids,
            embeddings = embeddings,
            documents  = texts,
            metadatas  = metadatas
        )

        print(f"  Stored batch {i // batch_size + 1} → {i + len(batch)}/{len(chunks)} chunks")

    print(f"'{collection_name}' ready — {len(chunks)} chunks indexed\n")


def query_collection(collection_name: str, query: str, n_results: int = 5) -> list[dict]:
    """
    Search a collection by natural language query.
    Returns the top n_results most relevant chunks.
    """
    collection = _get_or_create_collection(collection_name)

    query_embedding = MODEL.encode([query]).tolist()

    results = collection.query(
        query_embeddings = query_embedding,
        n_results        = n_results,
        include          = ["documents", "metadatas", "distances"]
    )

    # Zip results into clean dicts
    output = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        output.append({
            "text":     doc,
            "metadata": meta,
            "score":    round(1 - dist, 4)  # cosine distance → similarity score
        })

    return output

def clear_collection(name: str):
    """Delete a collection entirely so we can start fresh."""
    try:
        CLIENT.delete_collection(name)
        print(f"Cleared collection: '{name}'")
    except Exception:
        pass


CONTEXT_FILE = "project_context.json"

def save_project_context(context: dict):
    """Save project summary to disk so it persists between runs."""
    with open(CONTEXT_FILE, "w") as f:
        json.dump(context, f, indent=2)

def load_project_context() -> dict:
    """Load saved project summary. Returns empty dict if not found."""
    if not os.path.exists(CONTEXT_FILE):
        return {}
    with open(CONTEXT_FILE, "r") as f:
        return json.load(f)