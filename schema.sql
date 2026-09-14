-- KrishiRAG Mandi Prices PostgreSQL Schema
-- Defines the database schema and indexes for agricultural market price data.

CREATE TABLE IF NOT EXISTS mandi_prices (
    id SERIAL PRIMARY KEY,
    state VARCHAR(100) NOT NULL,
    district VARCHAR(100),
    market VARCHAR(150),
    commodity VARCHAR(100) NOT NULL,
    variety VARCHAR(100),
    grade VARCHAR(50),
    arrival_date DATE,
    min_price NUMERIC(10, 2),
    max_price NUMERIC(10, 2),
    modal_price NUMERIC(10, 2),
    fetched_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (state, district, market, commodity, variety, arrival_date)
);

-- Performance Indexes for search & filtering
CREATE INDEX IF NOT EXISTS idx_mandi_commodity ON mandi_prices (commodity);
CREATE INDEX IF NOT EXISTS idx_mandi_state_district ON mandi_prices (state, district);
CREATE INDEX IF NOT EXISTS idx_mandi_arrival_date ON mandi_prices (arrival_date);
