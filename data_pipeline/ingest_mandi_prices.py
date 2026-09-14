"""
KrishiRAG Mandi Price Ingestion Script
=======================================
This script ingests agricultural market (mandi) price data from the data.gov.in API
for the KrishiRAG farmer advisory system. It handles paginated fetching,
data cleaning, deduplication, and export to CSV format for downstream pipeline steps
(chunking, embedding, and FAISS indexing).
"""

import time
from typing import Any, Dict, List, Optional
import pandas as pd
import requests

# ==============================================================================
# Configuration
# ==============================================================================
API_KEY = "579b464db66ec23bdd000001ad4c372a5aec4c7f67f1f3bface521e1"
RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
LIMIT = 500  # Number of records per API request
OUTPUT_CSV = "mandi_prices_raw.csv"

BASE_URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def fetch_records(
    offset: int = 0,
    limit: int = LIMIT,
    state: Optional[str] = None,
    max_retries: int = 3,
    timeout: int = 60,
) -> Dict[str, Any]:
    """
    Fetch a single page of mandi price records from the data.gov.in resource API.

    Includes retry logic with exponential backoff for network resilience against API timeouts.

    Parameters:
        offset (int): The starting index offset for record retrieval.
        limit (int): Maximum number of records to retrieve per request.
        state (str, optional): Filter records by state (e.g. "Punjab").
        max_retries (int): Maximum number of retry attempts for failed requests.
        timeout (int): Request timeout in seconds.

    Returns:
        Dict[str, Any]: Parsed JSON response dictionary returned by the API.
    """
    params: Dict[str, Any] = {
        "api-key": API_KEY,
        "format": "json",
        "limit": limit,
        "offset": offset,
    }

    if state:
        params["filters[state.keyword]"] = state

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if attempt < max_retries:
                backoff = attempt * 2
                print(f"[Warning] Request failed (attempt {attempt}/{max_retries}): {e}. Retrying in {backoff}s...")
                time.sleep(backoff)
            else:
                print(f"[Error] Failed to fetch records at offset {offset} after {max_retries} attempts: {e}")
                raise


def fetch_all(max_records: int = 1000, state: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Paginate through API calls using `fetch_records` to retrieve up to `max_records`.

    Increments offset by LIMIT each iteration, pauses with time.sleep(0.5) between calls,
    and prints progress updates. Stops when no more records are returned or max_records is reached.

    Parameters:
        max_records (int): Maximum total records to collect.
        state (str, optional): Filter records by state name.

    Returns:
        List[Dict[str, Any]]: Consolidated list of raw record dictionaries.
    """
    records_acc: List[Dict[str, Any]] = []
    offset = 0

    print("==================================================")
    print("Starting Mandi Price Data Ingestion")
    print(f"Resource ID : {RESOURCE_ID}")
    print(f"Max Records : {max_records}")
    print(f"Batch Limit : {LIMIT}")
    if state:
        print(f"State Filter: {state}")
    print("==================================================\n")

    while len(records_acc) < max_records:
        fetch_limit = min(LIMIT, max_records - len(records_acc))
        print(f"-> Fetching batch: offset={offset}, limit={fetch_limit}...")

        data = fetch_records(offset=offset, limit=fetch_limit, state=state)
        records = data.get("records", [])

        if not records:
            print("No records returned from API. Reached end of available data.")
            break

        records_acc.extend(records)
        print(f"   Retrieved {len(records)} records. (Total collected: {len(records_acc)})")

        offset += LIMIT

        if len(records_acc) >= max_records:
            print(f"Reached requested max_records cap of {max_records}.")
            break

        time.sleep(0.5)

    print(f"\nCompleted fetching. Total records retrieved: {len(records_acc)}\n")
    return records_acc


def clean_and_save(records: List[Dict[str, Any]], output_path: str = OUTPUT_CSV) -> pd.DataFrame:
    """
    Convert raw records list to pandas DataFrame, clean column names,
    drop exact duplicates, write to CSV, and print a statistical overview.

    Parameters:
        records (List[Dict[str, Any]]): List of record dictionaries.
        output_path (str): File destination path for the saved CSV.

    Returns:
        pd.DataFrame: Cleaned pandas DataFrame.
    """
    if not records:
        print("[Warning] Records list is empty. Output dataset will be empty.")
        df = pd.DataFrame()
    else:
        df = pd.DataFrame(records)

    if not df.empty:
        # Standardize column names: lowercase and replace spaces/non-alphanumerics with underscores
        df.columns = (
            df.columns.astype(str)
            .str.strip()
            .str.lower()
            .str.replace(r"[\s\-\.]+", "_", regex=True)
            .str.replace(r"[^a-z0-9_]", "", regex=True)
        )

        # Drop exact duplicate rows
        initial_rows = len(df)
        df = df.drop_duplicates()
        dropped_duplicates = initial_rows - len(df)
        if dropped_duplicates > 0:
            print(f"Dropped {dropped_duplicates} exact duplicate row(s).")

    # Save to CSV
    df.to_csv(output_path, index=False)
    print(f"Data saved to: '{output_path}'")

    # Display dataset info
    print("\n--------------------------------------------------")
    print("Ingestion Summary")
    print("--------------------------------------------------")
    print(f"Row count    : {len(df)}")
    print(f"Column count : {len(df.columns)}")
    print(f"Column names : {list(df.columns)}")
    print("\nSample Row:")
    if not df.empty:
        print(df.head(1).to_dict(orient="records")[0])
    else:
        print("N/A (DataFrame is empty)")
    print("--------------------------------------------------\n")

    return df


if __name__ == "__main__":
    fetched_records = fetch_all(max_records=1000, state="Punjab")
    clean_and_save(fetched_records, OUTPUT_CSV)
