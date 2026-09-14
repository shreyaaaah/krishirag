"""
KrishiRAG Automated Pipeline Scheduler
=======================================
This script automatically runs the KrishiRAG mandi price data ingestion and 
PostgreSQL loading pipeline on a recurring schedule (every 6 hours).
It ensures the cloud PostgreSQL database (Neon) stays up to date with fresh mandi price data.
"""

import sys
import os
from datetime import datetime
import logging
from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler

# Load environment variables from .env file
load_dotenv()

# Ensure parent and module directories are in sys.path for robust imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from data_pipeline.ingest_mandi_prices import fetch_all, clean_and_save, OUTPUT_CSV
    from data_pipeline.load_to_postgres import load_csv, upsert_records
except ImportError:
    from ingest_mandi_prices import fetch_all, clean_and_save, OUTPUT_CSV
    from load_to_postgres import load_csv, upsert_records

# Configure logging format
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)


def run_pipeline() -> None:
    """
    Execute the full data pipeline:
    1. Ingest raw mandi price records from API and save to CSV.
    2. Load CSV data and upsert records into cloud PostgreSQL database.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logging.info(f"Starting scheduled KrishiRAG pipeline run at {timestamp}...")

    try:
        # Step 1: Ingestion
        logging.info("Step 1: Fetching mandi price records from data.gov.in API...")
        records = fetch_all(max_records=1000, state="Punjab")
        df_cleaned = clean_and_save(records, OUTPUT_CSV)
        logging.info(f"Step 1 Complete: Saved {len(df_cleaned)} cleaned records to '{OUTPUT_CSV}'.")

        # Step 2: Load to PostgreSQL
        logging.info("Step 2: Loading CSV data and upserting into PostgreSQL database...")
        df_csv = load_csv(OUTPUT_CSV)
        upserted_count = upsert_records(df_csv)
        logging.info(f"Step 2 Complete: Upserted {upserted_count} records into PostgreSQL.")

        end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logging.info(f"SUCCESS: Pipeline run completed successfully at {end_time}.\n")

    except Exception as e:
        end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logging.error(f"FAILURE: Pipeline run failed at {end_time}. Error: {e}", exc_info=True)


if __name__ == "__main__":
    scheduler = BlockingScheduler()

    # Schedule the job every 6 hours
    scheduler.add_job(run_pipeline, 'interval', hours=6)

    print("==================================================")
    print("KrishiRAG Data Pipeline Scheduler Started")
    print("Schedule: Every 6 hours")
    print("==================================================\n")

    # Perform an immediate initial run
    logging.info("Executing immediate initial pipeline run...")
    run_pipeline()

    print("\nScheduler loop running. Press Ctrl+C to exit.\n")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logging.info("Scheduler stopped by user. Graceful shutdown complete.")
