"""
KrishiRAG Advisory Text Chunking Script
=======================================
This script extracts text from crop advisory PDFs (PAU Package of Practices for Kharif and Rabi crops)
and splits them into clean, semantically meaningful chunks ready for embedding.
It serves as the unstructured knowledge base preparation stage before vector indexing (FAISS).
"""

import os
import json
import uuid
import re
import logging
from typing import List, Dict, Any
import pdfplumber

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

PDF_FOLDER = "data/advisories/"
OUTPUT_JSON = "advisory_chunks.json"

# Administrative/Boilerplate Keywords for Filtering
BOILERPLATE_KEYWORDS = [
    "copyright",
    "Regd. No.",
    "Price per copy",
    "Subscription for life",
    "no legal responsibility",
    "Additional Director Communication"
]


def is_boilerplate_or_front_matter(text: str, page_number: int) -> bool:
    """
    Filtering rule:
    1. Exclude front matter pages (page_number < 5, e.g. cover, title page, index/contents).
    2. Exclude chunks containing 2 or more administrative/boilerplate keywords.

    Note: The page-number cutoff (< 5) is easy to adjust here if needed.
    """
    if page_number < 5:
        return True

    text_lower = text.lower()
    matches = sum(1 for kw in BOILERPLATE_KEYWORDS if kw.lower() in text_lower)
    if matches >= 2:
        return True

    return False


def extract_text_from_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Extract text page by page from a PDF file using pdfplumber.

    Parameters:
        pdf_path (str): Path to the PDF file.

    Returns:
        List[Dict[str, Any]]: List of dicts with keys: page_number, text, source_file.
    """
    pages_data = []
    source_file = os.path.basename(pdf_path)

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                try:
                    text = page.extract_text() or ""
                    pages_data.append({
                        "page_number": i,
                        "text": text,
                        "source_file": source_file
                    })
                except Exception as page_err:
                    logging.warning(f"Failed to extract text from page {i} in '{source_file}': {page_err}")
    except Exception as pdf_err:
        logging.error(f"Could not open or process PDF file '{pdf_path}': {pdf_err}")

    return pages_data


def chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> List[str]:
    """
    Split page text into overlapping chunks along sentence and paragraph boundaries.

    Parameters:
        text (str): Raw extracted text from a page.
        chunk_size (int): Target maximum number of words per chunk (default: 400 words).
        overlap (int): Number of words to overlap between consecutive chunks (default: 50 words).

    Returns:
        List[str]: List of clean text chunks.
    """
    if not text or not text.strip():
        return []

    # Clean whitespace and linebreaks
    text = re.sub(r'\r\n|\r', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text).strip()

    # Split text by sentence endings or line breaks
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+|\n+', text) if s.strip()]

    chunks: List[str] = []
    current_sentences: List[str] = []
    current_word_count = 0

    for sentence in sentences:
        words_in_sentence = len(sentence.split())
        if not words_in_sentence:
            continue

        # If adding this sentence exceeds chunk_size limit and we already have accumulated sentences
        if current_word_count + words_in_sentence > chunk_size and current_sentences:
            chunk_str = " ".join(current_sentences).strip()
            # Skip short header/footer junk (under 20 words)
            if len(chunk_str.split()) >= 20:
                chunks.append(chunk_str)

            # Build overlap from trailing sentences of current chunk
            overlap_sentences: List[str] = []
            overlap_words = 0
            for prev_s in reversed(current_sentences):
                p_words = len(prev_s.split())
                if overlap_words + p_words <= overlap or not overlap_sentences:
                    overlap_sentences.insert(0, prev_s)
                    overlap_words += p_words
                else:
                    break

            current_sentences = overlap_sentences
            current_word_count = sum(len(s.split()) for s in current_sentences)

        current_sentences.append(sentence)
        current_word_count += words_in_sentence

    # Add remaining sentences
    if current_sentences:
        chunk_str = " ".join(current_sentences).strip()
        if len(chunk_str.split()) >= 20:
            chunks.append(chunk_str)

    return chunks


def process_all_pdfs(
    pdf_folder: str = PDF_FOLDER,
    output_json: str = OUTPUT_JSON
) -> tuple:
    """
    Iterate over all PDF files in pdf_folder, extract page texts, chunk them,
    apply front matter and boilerplate filters, attach metadata, and save to a JSON file.

    Parameters:
        pdf_folder (str): Folder path containing PDF documents.
        output_json (str): Destination path for final JSON output.

    Returns:
        tuple: (filtered_chunks, total_raw_chunks, total_removed_chunks)
    """
    if not os.path.exists(pdf_folder):
        logging.warning(f"PDF folder '{pdf_folder}' does not exist.")
        return [], 0, 0

    pdf_files = [
        os.path.join(pdf_folder, f)
        for f in os.listdir(pdf_folder)
        if f.lower().endswith(".pdf")
    ]

    if not pdf_files:
        logging.warning(f"No PDF files found in '{pdf_folder}'.")
        return [], 0, 0

    all_chunks: List[Dict[str, Any]] = []

    logging.info(f"Found {len(pdf_files)} PDF file(s) in '{pdf_folder}'. Processing...")

    for pdf_path in sorted(pdf_files):
        filename = os.path.basename(pdf_path)
        lower_name = filename.lower()

        # Infer season from filename
        if "kharif" in lower_name:
            season = "kharif"
        elif "rabi" in lower_name:
            season = "rabi"
        else:
            season = "unknown"

        logging.info(f"Processing '{filename}' (Season: {season})...")
        pages = extract_text_from_pdf(pdf_path)

        pdf_chunk_count = 0
        for page_info in pages:
            page_num = page_info["page_number"]
            page_text = page_info["text"]

            page_chunks = chunk_text(page_text, chunk_size=400, overlap=50)

            for chunk_str in page_chunks:
                chunk_record = {
                    "chunk_id": str(uuid.uuid4()),
                    "source_file": filename,
                    "page_number": page_num,
                    "season": season,
                    "text": chunk_str
                }
                all_chunks.append(chunk_record)
                pdf_chunk_count += 1

        logging.info(f"  -> Extracted {len(pages)} pages, generated {pdf_chunk_count} raw chunks.")

    total_before = len(all_chunks)
    filtered_chunks = [
        c for c in all_chunks
        if not is_boilerplate_or_front_matter(c["text"], c["page_number"])
    ]
    total_after = len(filtered_chunks)
    removed_count = total_before - total_after

    logging.info(f"Filtering complete: {total_before} raw chunks -> {total_after} valid chunks ({removed_count} removed).")

    # Save final JSON output
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(filtered_chunks, f, indent=2, ensure_ascii=False)

    logging.info(f"Saved {total_after} filtered chunks to '{output_json}'.")

    return filtered_chunks, total_before, removed_count


if __name__ == "__main__":
    folder = PDF_FOLDER
    out_file = OUTPUT_JSON

    chunks, total_before, removed_count = process_all_pdfs(pdf_folder=folder, output_json=out_file)

    pdf_files = [f for f in os.listdir(folder) if f.lower().endswith(".pdf")] if os.path.exists(folder) else []
    total_pdfs = len(pdf_files)
    total_after = len(chunks)

    if total_after > 0:
        word_counts = [len(c["text"].split()) for c in chunks]
        avg_words = sum(word_counts) / total_after
    else:
        avg_words = 0.0

    print("\n==================================================")
    print("KrishiRAG Advisory Chunking Summary (Filtered)")
    print("==================================================")
    print(f"Total PDFs Processed   : {total_pdfs}")
    print(f"Total Chunks (Before)  : {total_before}")
    print(f"Total Chunks (After)   : {total_after}")
    print(f"Total Chunks Removed   : {removed_count}")
    print(f"Average Chunk Length   : {avg_words:.1f} words")
    print("==================================================\n")

    if chunks:
        sample = chunks[0]
        print("--- SAMPLE CHUNK (FIRST ACTIVE CHUNK) ---")
        print(f"Chunk ID    : {sample['chunk_id']}")
        print(f"Source File : {sample['source_file']}")
        print(f"Page Number : {sample['page_number']}")
        print(f"Season      : {sample['season']}")
        print(f"Word Count  : {len(sample['text'].split())} words")
        print("Text Content:")
        print(sample['text'])
        print("--------------------\n")
