"""
KrishiRAG Retrieval Testing & Cross-Encoder Reranking Script
============================================================
Tests FAISS vector search against specific advisory queries and evaluates two-stage
retrieval using CrossEncoder (cross-encoder/ms-marco-MiniLM-L-6-v2) for relevance reranking.
"""

import os
import json
import logging
from typing import List, Dict, Any
import numpy as np
import faiss

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

INDEX_FILE = "faiss_index.bin"
METADATA_FILE = "chunk_metadata.json"
BI_ENCODER_MODEL = "all-MiniLM-L6-v2"
CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def load_index_and_metadata(
    index_file: str = INDEX_FILE,
    metadata_file: str = METADATA_FILE
) -> tuple:
    """Load FAISS vector index and chunk metadata list."""
    if not os.path.exists(index_file) or not os.path.exists(metadata_file):
        raise FileNotFoundError(f"FAISS index ('{index_file}') or metadata ('{metadata_file}') missing. Run embed_and_index.py first.")

    index = faiss.read_index(index_file)
    with open(metadata_file, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    return index, metadata


def search_faiss(
    query: str,
    index: faiss.Index,
    metadata: List[Dict[str, Any]],
    bi_encoder: Any,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """Perform dense vector retrieval via FAISS vector search."""
    query_vec = bi_encoder.encode([query], normalize_embeddings=True).astype(np.float32)
    scores, indices = index.search(query_vec, top_k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        item = metadata[idx].copy()
        item["faiss_score"] = float(score)
        results.append(item)
    return results


def rerank(
    query: str,
    candidates: List[Dict[str, Any]],
    cross_encoder: Any,
    top_k: int = 3
) -> List[Dict[str, Any]]:
    """
    Rerank candidate chunks using a CrossEncoder model.

    Parameters:
        query (str): Search query string.
        candidates (List[Dict]): Initial retrieved chunks from FAISS.
        cross_encoder (CrossEncoder): Pre-loaded CrossEncoder model.
        top_k (int): Number of top reranked items to return.

    Returns:
        List[Dict[str, Any]]: Top-k reranked candidates with 'rerank_score'.
    """
    if not candidates:
        return []
    if not cross_encoder:
        return candidates[:top_k]

    pairs = [[query, candidate["text"]] for candidate in candidates]
    cross_scores = cross_encoder.predict(pairs)

    reranked = []
    for candidate, score in zip(candidates, cross_scores):
        item = candidate.copy()
        item["rerank_score"] = float(score)
        reranked.append(item)

    reranked.sort(key=lambda x: x["rerank_score"], reverse=True)
    return reranked[:top_k]


def retrieve_and_rerank(
    query: str,
    index: faiss.Index,
    metadata: List[Dict[str, Any]],
    bi_encoder: Any,
    cross_encoder: Any,
    initial_k: int = 10,
    final_k: int = 3
) -> tuple:
    """
    Two-stage retrieval pipeline:
    1. Retrieve initial_k candidates using FAISS bi-encoder search.
    2. Rerank down to final_k using CrossEncoder scoring.

    Returns:
        tuple: (faiss_top_candidates, reranked_top_candidates)
    """
    faiss_candidates = search_faiss(query, index, metadata, bi_encoder, top_k=initial_k)
    reranked_results = rerank(query, faiss_candidates, cross_encoder, top_k=final_k)
    return faiss_candidates[:final_k], reranked_results


def print_results(title: str, results: List[Dict[str, Any]], show_rerank_score: bool = False) -> None:
    """Print formatted result list with scores and text snippets."""
    print(f"\n--- {title} ---")
    for rank, res in enumerate(results, start=1):
        score_str = f"FAISS Cosine: {res['faiss_score']:.4f}"
        if show_rerank_score and "rerank_score" in res:
            score_str += f" | Reranker Score: {res['rerank_score']:.4f}"

        snippet = res['text'][:200].replace('\n', ' ').strip() + ("..." if len(res['text']) > 200 else "")
        print(f"Result #{rank} ({score_str})")
        print(f"  Source : {res['source_file']} (Page {res['page_number']}) | Season: {res['season']}")
        print(f"  Chunk ID: {res['chunk_id']}")
        print(f"  Snippet: \"{snippet}\"")
        print("-" * 50)


if __name__ == "__main__":
    index, metadata = load_index_and_metadata()

    logging.info("Loading bi-encoder model ('all-MiniLM-L6-v2')...")
    bi_encoder = SentenceTransformer(BI_ENCODER_MODEL)

    logging.info("Loading cross-encoder model ('cross-encoder/ms-marco-MiniLM-L-6-v2')...")
    cross_encoder = CrossEncoder(CROSS_ENCODER_MODEL)

    part1_queries = [
        "sulfosulfuron dose for wheat",
        "Phalaris minor control in wheat",
        "pest control in cotton"
    ]

    print("\n==================================================")
    print("PART 1: FAISS-ONLY RETRIEVAL (TOP-5 RESULTS)")
    print("==================================================")

    for q in part1_queries:
        print(f"\nQUERY: '{q}'")
        faiss_top5 = search_faiss(q, index, metadata, bi_encoder, top_k=5)
        print_results(f"FAISS Top-5 for '{q}'", faiss_top5)

    all_queries = [
        "how to control weeds in wheat",
        "sulfosulfuron dose for wheat",
        "Phalaris minor control in wheat",
        "pest control in cotton"
    ]

    print("\n==================================================")
    print("PART 2: COMPARISON — FAISS-ONLY vs CROSS-ENCODER RERANKED")
    print("==================================================")

    for q in all_queries:
        print(f"\n==================================================")
        print(f"EVALUATING QUERY: '{q}'")
        print("==================================================")

        faiss_top3, reranked_top3 = retrieve_and_rerank(
            query=q,
            index=index,
            metadata=metadata,
            bi_encoder=bi_encoder,
            cross_encoder=cross_encoder,
            initial_k=10,
            final_k=3
        )

        print_results("FAISS-ONLY Top-3", faiss_top3)
        print_results("CROSS-ENCODER RERANKED Top-3", reranked_top3, show_rerank_score=True)
