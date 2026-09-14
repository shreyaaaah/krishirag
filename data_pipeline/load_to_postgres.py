"""
KrishiRAG - Load mandi price CSV data into PostgreSQL.
Handles upserts so daily re-runs don't create duplicates.
"""

import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values

load_dotenv()

# ==============================================================================
# Database Configuration
# ==============================================================================
DATABASE_URL = os.environ.get("NEON_DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("NEON_DATABASE_URL environment variable is not set.")

CSV_PATH = "mandi_prices_raw.csv"


def load_csv(path: str = CSV_PATH) -> pd.DataFrame:
    """
    Read mandi prices CSV and format arrival_date as date objects.

    Parameters:
        path (str): File path to raw CSV.

    Returns:
        pd.DataFrame: Loaded DataFrame with parsed dates.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"CSV file not found at path: '{path}'")

    df = pd.read_csv(path)

    if "arrival_date" in df.columns:
        df["arrival_date"] = pd.to_datetime(
            df["arrival_date"], format="%d/%m/%Y", errors="coerce"
        ).dt.date

    return df


def upsert_records(df: pd.DataFrame) -> int:
    """
    Upsert DataFrame records into the mandi_prices PostgreSQL table.
    Uses ON CONFLICT DO UPDATE on (state, district, market, commodity, variety, arrival_date).

    Parameters:
        df (pd.DataFrame): DataFrame containing mandi price records.

    Returns:
        int: Total number of upserted records.
    """
    if df.empty:
        print("[Warning] Provided DataFrame is empty. Skipping DB insertion.")
        return 0

    cols = [
        "state", "district", "market", "commodity",
        "variety", "grade", "arrival_date",
        "min_price", "max_price", "modal_price"
    ]

    # Fill NaN values with None for proper SQL NULL handling
    df_clean = df[cols].astype(object).where(pd.notnull(df[cols]), None)
    
    # Deduplicate within batch on unique constraint columns to prevent PostgreSQL CardinalityViolation
    conflict_cols = ["state", "district", "market", "commodity", "variety", "arrival_date"]
    df_clean = df_clean.drop_duplicates(subset=conflict_cols, keep="last")
    
    records = df_clean.values.tolist()

    query = """
        INSERT INTO mandi_prices
        (state, district, market, commodity, variety, grade,
         arrival_date, min_price, max_price, modal_price)
        VALUES %s
        ON CONFLICT (state, district, market, commodity, variety, arrival_date)
        DO UPDATE SET
            min_price = EXCLUDED.min_price,
            max_price = EXCLUDED.max_price,
            modal_price = EXCLUDED.modal_price,
            fetched_at = NOW();
    """

    print("Connecting to PostgreSQL database...")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    execute_values(cur, query, records)
    conn.commit()
    print(f"Upserted {len(records)} records into mandi_prices.")

    cur.close()
    conn.close()
    return len(records)


if __name__ == "__main__":
    try:
        df = load_csv()
        upsert_records(df)
    except FileNotFoundError as e:
        print(f"[Error] {e}")
    except psycopg2.OperationalError as e:
        print(f"[Database Error] Could not connect to PostgreSQL: {e}")
        print("Please check your NEON_DATABASE_URL environment variable or ensure PostgreSQL is running.")
