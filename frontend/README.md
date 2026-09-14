# KrishiRAG Frontend

Modern, responsive React + Vite + Tailwind CSS interface for the KrishiRAG Agricultural Advisory and Live Mandi Intelligence platform.

## Features
- **Grounded Advisory Chat Window**: Interactive chat interface for farmer queries with source citations (`pp_rabi.pdf, p.23`), response latency badges, and animated loading feedback.
- **Live Mandi Rates Widget**: Real-time market price lookup powered by Neon PostgreSQL with filtering by state, district, and commodity.
- **Modern Agriculture UI**: Curated emerald/earthy aesthetic, sleek scrollbars, and full mobile responsiveness.

## Quick Start Setup

1. **Install Dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Ensure Backend is Running**:
   In another terminal, ensure the FastAPI backend is running on `http://localhost:8000`:
   ```bash
   python backend/app/main.py
   ```

3. **Start Frontend Development Server**:
   ```bash
   npm run dev
   ```

4. **Access UI**:
   Open [http://localhost:5173](http://localhost:5173) in your web browser.
