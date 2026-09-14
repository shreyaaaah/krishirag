"""
KrishiRAG Query Logging Configuration
======================================
Sets up query logging to logs/queries.log for evaluation and MLOps query tracking.
"""

import os
import logging

LOGS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logs"))
os.makedirs(LOGS_DIR, exist_ok=True)
QUERY_LOG_PATH = os.path.join(LOGS_DIR, "queries.log")

# Setup dedicated query logger
query_logger = logging.getLogger("krishirag_query_logger")
query_logger.setLevel(logging.INFO)

if not query_logger.handlers:
    file_handler = logging.FileHandler(QUERY_LOG_PATH, encoding="utf-8")
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    file_handler.setFormatter(formatter)
    query_logger.addHandler(file_handler)


def log_query_event(query: str, response_time_ms: float, success: bool, sources_count: int = 0, error_msg: str = None) -> None:
    """
    Log query execution details to logs/queries.log.
    """
    status = "SUCCESS" if success else "FAILURE"
    log_line = f"Status: {status} | Latency: {response_time_ms:.2f}ms | Sources: {sources_count} | Query: '{query}'"
    if error_msg:
        log_line += f" | Error: {error_msg}"
    query_logger.info(log_line)
