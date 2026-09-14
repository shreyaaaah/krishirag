"""
KrishiRAG Chunk Inspection & Boilerplate Analysis Script
=========================================================
Loads advisory_chunks.json and inspects sample chunks at specific page targets
(pages 5, 30, 80, 150 for kharif and rabi PDFs). Also analyzes boilerplate/administrative content.
"""

import json
import os
from typing import List, Dict, Any

CHUNKS_FILE = "advisory_chunks.json"

BOILERPLATE_KEYWORDS = [
    "copyright",
    "Regd. No.",
    "Price per copy",
    "Subscription for life",
    "no legal responsibility",
    "Additional Director Communication"
]


def load_chunks(filepath: str = CHUNKS_FILE) -> List[Dict[str, Any]]:
    if not os.path.exists(filepath):
        print(f"[Error] '{filepath}' not found.")
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def find_closest_chunk(chunks: List[Dict[str, Any]], source_file: str, target_page: int) -> Dict[str, Any]:
    file_chunks = [c for c in chunks if c["source_file"].lower() == source_file.lower()]
    if not file_chunks:
        return None
    return min(file_chunks, key=lambda c: abs(c["page_number"] - target_page))


def inspect_sample_chunks(chunks: List[Dict[str, Any]]) -> None:
    targets = [5, 30, 80, 150]
    sources = ["pp_kharif.pdf", "pp_rabi.pdf"]

    print("==================================================")
    print("SAMPLE CHUNKS INSPECTION")
    print("==================================================\n")

    for source in sources:
        print(f">>> File: {source}")
        for target_page in targets:
            chunk = find_closest_chunk(chunks, source, target_page)
            if chunk:
                words = len(chunk["text"].split())
                print(f"\n--- Target Page ~{target_page} (Actual Page: {chunk['page_number']}) ---")
                print(f"Chunk ID    : {chunk['chunk_id']}")
                print(f"Source File : {chunk['source_file']}")
                print(f"Page Number : {chunk['page_number']}")
                print(f"Season      : {chunk['season']}")
                print(f"Word Count  : {words} words")
                print("Text:")
                print(chunk["text"])
                print("-" * 50)
            else:
                print(f"No chunk found for {source} around page {target_page}.")
        print("\n")


def analyze_boilerplate(chunks: List[Dict[str, Any]]) -> None:
    print("==================================================")
    print("BOILERPLATE & ADMINISTRATIVE KEYWORD ANALYSIS")
    print("==================================================")

    matched_chunks = []

    for c in chunks:
        text_lower = c["text"].lower()
        matched_words = [kw for kw in BOILERPLATE_KEYWORDS if kw.lower() in text_lower]
        if matched_words:
            matched_chunks.append({
                "chunk_id": c["chunk_id"],
                "source_file": c["source_file"],
                "page_number": c["page_number"],
                "matched_keywords": matched_words,
                "keyword_count": len(matched_words)
            })

    print(f"Total Chunks Analyzed           : {len(chunks)}")
    print(f"Chunks Containing Boilerplate   : {len(matched_chunks)}")
    print("--------------------------------------------------")

    for match in matched_chunks:
        print(f"Chunk ID: {match['chunk_id']} | File: {match['source_file']} | Page: {match['page_number']} | Matches ({match['keyword_count']}): {', '.join(match['matched_keywords'])}")

    print("==================================================\n")


if __name__ == "__main__":
    chunks_data = load_chunks()
    if chunks_data:
        inspect_sample_chunks(chunks_data)
        analyze_boilerplate(chunks_data)
