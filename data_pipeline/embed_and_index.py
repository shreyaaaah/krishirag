"""
KrishiRAG Embedding and FAISS Vector Indexing Script
====================================================
Loads filtered advisory chunks from advisory_chunks.json, computes 384-dimensional
dense vector embeddings using sentence-transformers (all-MiniLM-L6-v2), and builds a
local FAISS vector index for fast semantic similarity retrieval.
Saves the FAISS index to faiss_index.bin and parallel metadata to chunk_metadata.json.
"""

import os
import json
import time
import logging
from typing import List, Dict, Any
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

INPUT_CHUNKS_FILE = "advisory_chunks.json"
INDEX_FILE = "faiss_index.bin"
METADATA_FILE = "chunk_metadata.json"
MODEL_NAME = "all-MiniLM-L6-v2"


def load_chunks(filepath: str = INPUT_CHUNKS_FILE) -> List[Dict[str, Any]]:
    """
    Load json chunk records from filepath.

    Parameters:
        filepath (str): Input json file path containing advisory chunks.

    Returns:
        List[Dict[str, Any]]: List of chunk dictionaries.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Input chunks file '{filepath}' not found. Please run chunk_advisories.py first.")
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def build_embeddings_and_index(
    chunks: List[Dict[str, Any]],
    model_name: str = MODEL_NAME,
    batch_size: int = 32
) -> tuple:
    """
    Generate vector embeddings in batches using sentence-transformers and index them with FAISS.

    Parameters:
        chunks (List[Dict]): List of chunk dicts containing 'text' and metadata.
        model_name (str): SentenceTransformer model identifier.
        batch_size (int): Batch size for embedding generation.

    Returns:
        tuple: (faiss_index, metadata_list, elapsed_seconds, embedding_dim)
    """
    logging.info(f"Loading SentenceTransformer model '{model_name}'...")
    model = SentenceTransformer(model_name)

    texts = [c["text"] for c in chunks]
    logging.info(f"Generating embeddings for {len(texts)} chunks (batch size={batch_size})...")

    start_time = time.time()
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        normalize_embeddings=True
    )
    elapsed = time.time() - start_time

    embeddings = np.array(embeddings, dtype=np.float32)
    dim = embeddings.shape[1]
    logging.info(f"Generated embeddings array of shape {embeddings.shape} in {elapsed:.2f} seconds.")

    # Build FAISS Inner Product index (for L2-normalized vectors, Inner Product == Cosine Similarity)
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    logging.info(f"Built FAISS IndexFlatIP with {index.ntotal} vectors of dimension {dim}.")

    # Metadata list in matching position order
    metadata = [
        {
            "chunk_id": c["chunk_id"],
            "source_file": c["source_file"],
            "page_number": c["page_number"],
            "season": c["season"],
            "text": c["text"]
        }
        for c in chunks
    ]

    return index, metadata, elapsed, dim


def save_index_and_metadata(
    index: faiss.Index,
    metadata: List[Dict[str, Any]],
    index_file: str = INDEX_FILE,
    metadata_file: str = METADATA_FILE
) -> None:
    """
    Save FAISS binary index and metadata JSON file.

    Parameters:
        index (faiss.Index): Populated FAISS index.
        metadata (List[Dict]): List of chunk metadata dicts aligned by index.
        index_file (str): Target FAISS index file path.
        metadata_file (str): Target metadata JSON file path.
    """
    faiss.write_index(index, index_file)
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    logging.info(f"Saved FAISS index to '{index_file}' and metadata to '{metadata_file}'.")


def test_retrieval(
    query: str,
    model_name: str = MODEL_NAME,
    index_file: str = INDEX_FILE,
    metadata_file: str = METADATA_FILE,
    k: int = 3
) -> None:
    """
    Test vector retrieval for a natural language query against the saved FAISS index.

    Parameters:
        query (str): The search query text.
        model_name (str): SentenceTransformer model name.
        index_file (str): FAISS index file path.
        metadata_file (str): Metadata JSON file path.
        k (int): Number of top results to retrieve.
    """
    print("\n==================================================")
    print(f"TEST RETRIEVAL QUERY: '{query}'")
    print("==================================================")

    if not os.path.exists(index_file) or not os.path.exists(metadata_file):
        print("[Error] FAISS index or metadata file not found.")
        return

    index = faiss.read_index(index_file)
    with open(metadata_file, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    model = SentenceTransformer(model_name)
    query_vec = model.encode([query], normalize_embeddings=True).astype(np.float32)

    scores, indices = index.search(query_vec, k)

    for rank, (score, idx) in enumerate(zip(scores[0], indices[0]), start=1):
        item = metadata[idx]
        print(f"\nResult #{rank} (Cosine Similarity Score: {score:.4f})")
        print(f"  Source File : {item['source_file']} (Page {item['page_number']})")
        print(f"  Season      : {item['season']}")
        print(f"  Chunk ID    : {item['chunk_id']}")
        print("  Snippet:")
        snippet = item['text'][:350] + ("..." if len(item['text']) > 350 else "")
        print(f"  \"{snippet}\"")
        print("-" * 50)


if __name__ == "__main__":
    chunks = load_chunks(INPUT_CHUNKS_FILE)
    index, metadata, elapsed_sec, dim = build_embeddings_and_index(chunks)
    save_index_and_metadata(index, metadata, INDEX_FILE, METADATA_FILE)

    print("\n==================================================")
    print("KrishiRAG Embedding & Indexing Summary")
    print("==================================================")
    print(f"Total Chunks Embedded : {len(chunks)}")
    print(f"Embedding Dimension   : {dim}")
    print(f"Time Taken            : {elapsed_sec:.2f} seconds")
    print(f"FAISS Index Saved     : {INDEX_FILE}")
    print(f"Metadata Saved        : {METADATA_FILE}")
    print("==================================================\n")

    # Run test retrieval
    test_retrieval("how to control weeds in wheat", k=3)
