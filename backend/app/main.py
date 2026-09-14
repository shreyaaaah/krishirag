"""
KrishiRAG FastAPI Application Main Entrypoint
=============================================
Exposes RAG query generation, health status monitoring, and structured live mandi price data endpoints.
"""

import sys
import os
import time
import logging
from datetime import datetime
from typing import Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Setup system path to locate project modules
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Load environment variables
load_dotenv(os.path.join(PROJECT_ROOT, ".env"), override=True)

# Import backend modules
from fastapi.responses import StreamingResponse
from backend.app.models import (
    QueryRequest,
    QueryResponse,
    SourceInfo,
    MandiPriceResponse,
    MandiPriceRecord
)
from backend.app.logging_config import log_query_event
from backend.rag.generator import generate_answer, generate_answer_stream

# Initialize FastAPI App
app = FastAPI(
    title="KrishiRAG API",
    description="Farmer advisory RAG system and live mandi price lookup service",
    version="1.0.0"
)

# Enable CORS for development and production
allowed_origins_raw = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000")
if allowed_origins_raw.strip() == "*":
    allowed_origins = ["*"]
else:
    allowed_origins = [o.strip() for o in allowed_origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", summary="Uptime Monitoring Health Check")
def health_check():
    """Returns current API health status and timestamp."""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/query", response_model=QueryResponse, summary="KrishiRAG Farmer Advisory RAG Query")
def query_advisory(req: QueryRequest):
    """
    Retrieves relevant crop advisory chunks, reranks context, and synthesizes a grounded answer via Groq LLM.
    """
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")

    start_time = time.time()
    try:
        result = generate_answer(req.query.strip())
        latency_ms = (time.time() - start_time) * 1000.0

        # Check for system/API errors
        answer_text = result.get("answer", "")
        if answer_text.startswith("System Error:") or answer_text.startswith("Groq API Error:"):
            log_query_event(req.query, latency_ms, success=False, error_msg=answer_text)
            raise HTTPException(status_code=500, detail=answer_text)

        sources = [
            SourceInfo(file=s["file"], page=s["page"])
            for s in result.get("sources", [])
        ]
        log_query_event(req.query, latency_ms, success=True, sources_count=len(sources))

        return QueryResponse(
            answer=answer_text,
            sources=sources,
            response_time_ms=round(latency_ms, 2)
        )
    except HTTPException:
        raise
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000.0
        log_query_event(req.query, latency_ms, success=False, error_msg=str(e))
        raise HTTPException(status_code=500, detail=f"RAG Pipeline Error: {str(e)}")


@app.post("/api/query/stream", summary="KrishiRAG Farmer Advisory SSE Streaming Endpoint")
def query_advisory_stream(req: QueryRequest):
    """
    Streams RAG response word-by-word using Server-Sent Events (SSE).
    """
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")

    return StreamingResponse(
        generate_answer_stream(req.query.strip()),
        media_type="text/event-stream"
    )


def fetch_mandi_records_with_retry(database_url: str, query_sql: str, params: list, max_attempts: int = 2) -> list:
    """
    Executes a mandi prices SQL query using a fresh psycopg2 connection.
    Includes a retry mechanism (max 2 attempts) catching OperationalError and InterfaceError
    to handle Neon DB cold-start / SSL SYSCALL EOF errors smoothly.
    """
    last_exception = None
    for attempt in range(1, max_attempts + 1):
        conn = None
        cur = None
        try:
            logging.info(f"[DB Attempt {attempt}/{max_attempts}] Connecting to Neon PostgreSQL...")
            conn = psycopg2.connect(database_url, connect_timeout=10)
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(query_sql, params)
            rows = cur.fetchall()
            return rows
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as db_err:
            last_exception = db_err
            logging.warning(
                f"[DB Attempt {attempt}/{max_attempts}] Database connection error ({type(db_err).__name__}): {db_err}. "
                f"{'Retrying in 1 second...' if attempt < max_attempts else 'Max retry attempts reached.'}"
            )
            if attempt < max_attempts:
                time.sleep(1.0)
        except Exception as e:
            last_exception = e
            logging.error(f"Unexpected database error: {e}")
            raise
        finally:
            if cur:
                try:
                    cur.close()
                except Exception:
                    pass
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    if last_exception:
        raise last_exception


@app.get("/api/mandi-prices", response_model=MandiPriceResponse, summary="Live Mandi Price Lookup")
def get_mandi_prices(
    state: Optional[str] = None,
    district: Optional[str] = None,
    commodity: Optional[str] = None
):
    """
    Queries the PostgreSQL mandi_prices table directly via psycopg2 using NEON_DATABASE_URL.
    Uses fresh connections per request with automatic retry logic for Neon cold-starts.
    """
    database_url = os.environ.get("NEON_DATABASE_URL")
    if not database_url:
        raise HTTPException(status_code=500, detail="NEON_DATABASE_URL environment variable is missing.")

    query_sql = """
        SELECT 
            id, state, district, market, commodity, variety, grade,
            arrival_date::text, min_price::float, max_price::float, modal_price::float,
            fetched_at::text
        FROM mandi_prices
        WHERE 1=1
    """
    params = []

    if state:
        query_sql += " AND LOWER(state) = LOWER(%s)"
        params.append(state.strip())
    if district:
        query_sql += " AND LOWER(district) = LOWER(%s)"
        params.append(district.strip())
    if commodity:
        query_sql += " AND LOWER(commodity) LIKE LOWER(%s)"
        params.append(f"%{commodity.strip()}%")

    query_sql += " ORDER BY arrival_date DESC, state ASC, commodity ASC LIMIT 100;"

    try:
        rows = fetch_mandi_records_with_retry(database_url, query_sql, params, max_attempts=2)
        records = [MandiPriceRecord(**row) for row in rows]
        return MandiPriceResponse(total=len(records), data=records)
    except Exception as e:
        logging.error(f"Database lookup failed after retries: {e}")
        raise HTTPException(status_code=500, detail=f"Database Lookup Error: {str(e)}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
