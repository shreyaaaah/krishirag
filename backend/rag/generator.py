"""
KrishiRAG RAG Generator Module
==============================
Combines dense vector retrieval (FAISS + CrossEncoder reranker) with LLM synthesis (Groq API)
to provide grounded, cited, and farmer-friendly agricultural advisory responses.
"""

import sys
import os
import logging
from typing import List, Dict, Any, Optional

# Ensure UTF-8 output encoding for Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from groq import Groq, GroqError

# Ensure project root and data_pipeline directory are in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
DATA_PIPELINE_DIR = os.path.join(PROJECT_ROOT, "data_pipeline")

# Load environment variables from .env
load_dotenv(os.path.join(PROJECT_ROOT, ".env"), override=True)

if DATA_PIPELINE_DIR not in sys.path:
    sys.path.insert(0, DATA_PIPELINE_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import retrieval & reranking functions
try:
    from data_pipeline.test_retrieval_queries import (
        load_index_and_metadata,
        retrieve_and_rerank,
        BI_ENCODER_MODEL,
        CROSS_ENCODER_MODEL
    )
except ImportError:
    from test_retrieval_queries import (
        load_index_and_metadata,
        retrieve_and_rerank,
        BI_ENCODER_MODEL,
        CROSS_ENCODER_MODEL
    )

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Global lazy-loaded resources
_INDEX = None
_METADATA = None
_BI_ENCODER = None
_CROSS_ENCODER = None
_GROQ_CLIENT = None


def get_resources():
    """Lazy-load FAISS index, metadata, bi-encoder, cross-encoder, and Groq client."""
    global _INDEX, _METADATA, _BI_ENCODER, _CROSS_ENCODER, _GROQ_CLIENT

    if _INDEX is None or _METADATA is None:
        index_path = os.path.join(PROJECT_ROOT, "faiss_index.bin")
        meta_path = os.path.join(PROJECT_ROOT, "chunk_metadata.json")
        _INDEX, _METADATA = load_index_and_metadata(index_path, meta_path)

    if _BI_ENCODER is None or _CROSS_ENCODER is None:
        try:
            import torch
            torch.set_num_threads(1)
            torch.set_grad_enabled(False)
        except Exception:
            pass
        from sentence_transformers import SentenceTransformer, CrossEncoder
        if _BI_ENCODER is None:
            _BI_ENCODER = SentenceTransformer(BI_ENCODER_MODEL, device="cpu")
        if _CROSS_ENCODER is None:
            _CROSS_ENCODER = CrossEncoder(CROSS_ENCODER_MODEL, device="cpu")

    if _GROQ_CLIENT is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if api_key and api_key != "your_key_here":
            _GROQ_CLIENT = Groq(api_key=api_key)

    return _INDEX, _METADATA, _BI_ENCODER, _CROSS_ENCODER, _GROQ_CLIENT


def build_prompt(query: str, retrieved_chunks: List[Dict[str, Any]]) -> str:
    """
    Construct system instructions and grounded context prompt for the LLM.

    Parameters:
        query (str): The farmer's input query.
        retrieved_chunks (List[Dict]): Chunks with text, source_file, page_number.

    Returns:
        str: Formatted prompt string.
    """
    context_blocks = []
    for chunk in retrieved_chunks:
        source_label = f"[Source: {chunk['source_file']}, Page {chunk['page_number']}]"
        context_blocks.append(f"{source_label}\n{chunk['text']}")

    context_str = "\n\n".join(context_blocks)

    prompt = f"""You are a warm, knowledgeable agricultural advisor texting with a farmer. Reply exactly like a helpful person would text back — natural flowing sentences, no markdown tables, no pipe characters, no bolded headers or titles, no "What to do / How to do it / Why / Source" structured format.

Rules:
- Read the farmer's message naturally, the way a person would. If it's casual conversation — a greeting, thanks, small talk, a farewell, or any message that isn't really a farming question — respond warmly and naturally in kind, the way a friendly person would text back, without forcing in farming advice or citing sources. Match their energy: if they're casual, be casual back. Ignore any retrieved context when the message is casual conversation.
- If it's a genuine farming/crop question, answer using the grounded retrieval process as normal. Mention sources naturally inside a sentence (e.g., "According to PAU's Rabi guide...").
- If it's clearly unrelated to farming (general knowledge, random topics), gently redirect — mention you're focused on crop and farming advice based on Punjab's agricultural advisory guides, and ask if they have a farming question you can help with instead.
- You decide which of these three cases applies based on the actual message and conversation flow — don't rely on fixed keyword matching, use natural understanding the way a person would.
- Start directly with a natural sentence — never a bolded title.
- Use bullets only if listing 3+ genuinely distinct items, and keep them minimal — never a formal table.
- If the question is ambiguous or missing key details needed to give an accurate answer (for example: crop not specified, season not specified, location not specified when it matters), do NOT guess or default to something. Instead, ask a short, specific, natural clarifying question — the way a helpful person would ask "which crop are you asking about — wheat, rice, cotton?" before answering.
- Keep answers concise — a few natural sentences for simple questions.
- Stay strictly grounded in retrieved context when answering farming questions — never invent information.

CONTEXT:
{context_str}

FARMER'S QUESTION:
{query}

NATURAL TEXT REPLY:"""

    print(f"\n==========================================")
    print(f"[DEBUG] Final System Prompt Being Sent To LLM:")
    print(f"==========================================\n{prompt}\n")
    logging.info(f"[DEBUG] Final system prompt being sent to LLM:\n{prompt}")
    return prompt


DEFAULT_MODEL = os.environ.get("GROQ_MODEL", "qwen/qwen3.8-27b")


def generate_answer(
    query: str,
    top_k: int = 3,
    model_name: str = DEFAULT_MODEL
) -> Dict[str, Any]:
    """
    Execute full RAG pipeline: Retrieve, Rerank, Prompt Construction, and Groq LLM Generation.

    Parameters:
        query (str): User question.
        top_k (int): Number of top reranked chunks to use as context.
        model_name (str): Groq model identifier (default: qwen/qwen3.8-27b).

    Returns:
        Dict[str, Any]: Dict containing "answer", "sources", and "raw_chunks_used".
    """
    try:
        index, metadata, bi_encoder, cross_encoder, client = get_resources()
    except Exception as err:
        logging.error(f"Resource initialization failed: {err}")
        return {
            "answer": f"System Error: {err}",
            "sources": [],
            "raw_chunks_used": []
        }

    try:
        # Retrieve & rerank
        _, reranked_chunks = retrieve_and_rerank(
            query=query,
            index=index,
            metadata=metadata,
            bi_encoder=bi_encoder,
            cross_encoder=cross_encoder,
            initial_k=10,
            final_k=top_k
        )

        if not reranked_chunks:
            reranked_chunks = []

        # Extract unique sources used
        sources = []
        seen = set()
        for chunk in reranked_chunks:
            src_key = (chunk["source_file"], chunk["page_number"])
            if src_key not in seen:
                seen.add(src_key)
                sources.append({"file": chunk["source_file"], "page": chunk["page_number"]})

        # Build prompt
        prompt = build_prompt(query, reranked_chunks)

        # Call Groq API if key is present
        if client:
            candidate_models = [model_name, "qwen/qwen3.8-27b", "openai/gpt-oss-20b", "groq/compound-mini", "groq/compound"]
            # Deduplicate preserving order
            unique_models = []
            for m in candidate_models:
                if m not in unique_models:
                    unique_models.append(m)

            answer_text = None
            used_model = model_name

            for target_model in unique_models:
                try:
                    chat_completion = client.chat.completions.create(
                        messages=[{"role": "user", "content": prompt}],
                        model=target_model,
                        temperature=0.3,
                        max_tokens=800
                    )
                    answer_text = chat_completion.choices[0].message.content.strip()
                    used_model = target_model
                    break
                except Exception as model_err:
                    logging.warning(f"Groq API model '{target_model}' failed: {model_err}. Trying fallback...")
                    continue

            if answer_text is None:
                raise RuntimeError("All Groq LLM model attempts failed.")
        else:
            used_model = "None (No API Key)"
            answer_text = (
                "[Notice: GROQ_API_KEY is not set in .env. Please set GROQ_API_KEY=your_key in .env to generate LLM answers.]\n\n"
                f"--- CONTEXT RETRIEVED & PROMPT BUILT ---\n{prompt}"
            )

        return {
            "answer": answer_text,
            "sources": sources,
            "raw_chunks_used": reranked_chunks,
            "model": used_model
        }

    except GroqError as ge:
        logging.error(f"Groq API Error: {ge}")
        return {
            "answer": f"Groq API Error: {ge}",
            "sources": [],
            "raw_chunks_used": [],
            "model": model_name
        }
    except Exception as e:
        logging.error(f"Unexpected Error during generation: {e}")
        return {
            "answer": f"Generation Error: {e}",
            "sources": [],
            "raw_chunks_used": [],
            "model": model_name
        }


def generate_answer_stream(
    query: str,
    top_k: int = 3,
    model_name: str = DEFAULT_MODEL
):
    """
    Generator function yielding Server-Sent Events (SSE) data lines as Groq streams chunks.

    Yields:
        f"data: {json.dumps({'chunk': text})}\n\n"
        f"data: {json.dumps({'done': True, 'sources': sources, 'response_time_ms': latency})}\n\n"
    """
    import json
    import time

    start_t = time.time()
    try:
        index, metadata, bi_encoder, cross_encoder, client = get_resources()
    except Exception as err:
        logging.error(f"Resource initialization failed: {err}")
        yield f"data: {json.dumps({'chunk': f'System Error: {err}'})}\n\n"
        yield f"data: {json.dumps({'done': True, 'sources': []})}\n\n"
        return

    try:
        # Retrieve & rerank
        _, reranked_chunks = retrieve_and_rerank(
            query=query,
            index=index,
            metadata=metadata,
            bi_encoder=bi_encoder,
            cross_encoder=cross_encoder,
            initial_k=10,
            final_k=top_k
        )

        if not reranked_chunks:
            reranked_chunks = []

        # Extract unique sources used
        sources = []
        seen = set()
        for chunk in reranked_chunks:
            src_key = (chunk["source_file"], chunk["page_number"])
            if src_key not in seen:
                seen.add(src_key)
                sources.append({"file": chunk["source_file"], "page": chunk["page_number"]})

        # Build prompt
        prompt = build_prompt(query, reranked_chunks)

        if client:
            candidate_models = [model_name, "qwen/qwen3.8-27b", "openai/gpt-oss-20b", "groq/compound-mini", "groq/compound"]
            unique_models = []
            for m in candidate_models:
                if m not in unique_models:
                    unique_models.append(m)

            streamed_success = False
            for target_model in unique_models:
                try:
                    response_stream = client.chat.completions.create(
                        messages=[{"role": "user", "content": prompt}],
                        model=target_model,
                        temperature=0.3,
                        max_tokens=800,
                        stream=True
                    )
                    for chunk in response_stream:
                        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                            text_piece = chunk.choices[0].delta.content
                            yield f"data: {json.dumps({'chunk': text_piece})}\n\n"
                            time.sleep(0.015)
                    streamed_success = True
                    break
                except Exception as model_err:
                    logging.warning(f"Groq stream model '{target_model}' failed: {model_err}. Trying fallback...")
                    continue

            if not streamed_success:
                yield f"data: {json.dumps({'chunk': 'System Error: All Groq LLM streaming model attempts failed.'})}\n\n"
        else:
            yield f"data: {json.dumps({'chunk': '[Notice: GROQ_API_KEY is not set in .env.]\n\n' + prompt})}\n\n"

        latency_ms = (time.time() - start_t) * 1000.0
        yield f"data: {json.dumps({'done': True, 'sources': sources, 'response_time_ms': round(latency_ms, 2)})}\n\n"

    except Exception as e:
        logging.error(f"Unexpected streaming error: {e}")
        yield f"data: {json.dumps({'chunk': f'Streaming Error: {e}'})}\n\n"
        yield f"data: {json.dumps({'done': True, 'sources': []})}\n\n"


if __name__ == "__main__":
    import time

    test_queries = [
        "What is the dose of sulfosulfuron for wheat?",
        "How do I control whitefly in cotton?",
        "When should I sow wheat in Punjab?"
    ]

    default_model = DEFAULT_MODEL

    print("==================================================")
    print("KrishiRAG RAG Generator Execution")
    print(f"Target Groq LLM Model : {default_model}")
    print("==================================================\n")

    for idx, q in enumerate(test_queries, start=1):
        print(f"==================================================")
        print(f"QUERY #{idx}: '{q}'")
        print("==================================================")
        
        start_t = time.time()
        result = generate_answer(q, top_k=3, model_name=default_model)
        latency = time.time() - start_t

        print(f"\n[Model Used]: {result.get('model', default_model)}")
        print(f"[Response Time]: {latency:.2f} seconds")

        print("\n--- GENERATED ANSWER ---")
        print(result["answer"])

        print("\n--- CITED SOURCES ---")
        if result["sources"]:
            for s in result["sources"]:
                print(f"- File: {s['file']}, Page: {s['page']}")
        else:
            print("No sources cited / Error occurred.")

        print("\n--- GROUNDING CHECK (RAW CHUNKS USED) ---")
        for chunk_idx, raw_c in enumerate(result["raw_chunks_used"], start=1):
            print(f"  Chunk #{chunk_idx} [{raw_c['source_file']}, Page {raw_c['page_number']}] (Season: {raw_c['season']}):")
            snippet = raw_c['text'][:180].replace('\n', ' ') + ("..." if len(raw_c['text']) > 180 else "")
            print(f"  \"{snippet}\"")
        print("==================================================\n")
